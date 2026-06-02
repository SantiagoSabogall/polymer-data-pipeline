import requests

mi_informacion = {"nombre": "Equipo de Investigación", "proyecto": "Polímeros"}

# Enviamos los datos al servidor
respuesta = requests.post("https://httpbin.org/post", json=mi_informacion)

print(respuesta.status_code)