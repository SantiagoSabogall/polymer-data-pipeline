"""Helpers HTTP reutilizables: sessions con reintentos y paginación genérica.

Evita duplicar el while-loop de paginación que antes vivía en cada fetcher
(Crossref/Springer/Elsevier) y unifica la política de reintentos con backoff
para todos los fetchers.
"""

import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def make_session(
    retries: int = 3,
    backoff_factor: float = 1.0,
    status_forcelist: tuple[int, ...] = (429, 500, 502, 503, 504),
) -> requests.Session:
    """Devuelve una ``requests.Session`` con reintentos y backoff exponencial.

    El adapter de urllib3 reintenta los códigos de ``status_forcelist`` con
    espera ``backoff_factor * 2**attempt`` y respeta la cabecera ``Retry-After``.
    """
    retry = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=list(status_forcelist),
        raise_on_status=False,
    )
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


class PageFetcher:
    """Pagina una API que devuelve lotes por ``start``/``offset``.

    Encapsula el patrón común de Crossref/Springer/Elsevier: recorrer lotes de
    ``batch_size`` hasta ``total_limit``, sin romper en un solo fallo.

    ``build_params(start)`` -> dict de params para el lote que empieza en
    ``start``. ``extract_items(data)`` -> lista u objetos a acumular.
    ``extract_total(data)`` -> entero con el total de resultados disponible.
    """

    def __init__(
        self,
        *,
        url: str,
        batch_size: int,
        sleep_between: float,
        total_limit: int,
        build_params,
        extract_items,
        extract_total,
        name: str = "API",
        initial_start: int = 0,
    ) -> None:
        self.url = url
        self.batch_size = batch_size
        self.sleep_between = sleep_between
        self.total_limit = total_limit
        self.build_params = build_params
        self.extract_items = extract_items
        self.extract_total = extract_total
        self.name = name
        self.initial_start = initial_start

    def run(self, session: requests.Session, start: int | None = None) -> list:
        normalized: list = []
        cur = self.initial_start if start is None else start
        while cur < self.total_limit:
            params = self.build_params(cur)
            try:
                resp = session.get(self.url, params=params, timeout=15)
            except requests.RequestException as e:
                print(f"[{self.name}] Falló la petición en start={cur}: {e}")
                cur += self.batch_size
                continue

            if resp.status_code == 429:
                # El adapter de retries normalmente ya lo gestionó; guard por si llega.
                print(f"[{self.name}] 429 en start={cur}. Pausando 5s y saltando el lote.")
                time.sleep(5)
                cur += self.batch_size
                continue

            if resp.status_code != 200:
                print(f"[{self.name}] Error {resp.status_code} en start={cur}. Se omite el lote.")
                cur += self.batch_size
                continue

            try:
                data = resp.json()
            except ValueError:
                print(f"[{self.name}] Respuesta no JSON en start={cur}. Se omite el lote.")
                cur += self.batch_size
                continue

            items = self.extract_items(data)
            if not items:
                break

            normalized.extend(items)

            total = self.extract_total(data)
            if len(normalized) >= total:
                break

            cur += self.batch_size
            if self.sleep_between:
                time.sleep(self.sleep_between)
        return normalized