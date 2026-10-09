# Pruebas

`unit/` comprobará reglas y transformaciones aisladas; `integration/` comprobará recorridos completos con muestras pequeñas y permitidas.

Las pruebas unitarias ya existen en `unit/`. El recorrido de integración todavía está pendiente. Consultar la [guía de pruebas y reproducción](../docs/pruebas-reproduccion.md) para instalar el entorno completo con `scripts/setup_env.ps1` (incluido `httpx` para TestClient), ejecutar la suite y probar scripts, API y panel. `.github/workflows/tests.yml` ejecuta estas pruebas en cada push y PR usando Windows/Python 3.12.
