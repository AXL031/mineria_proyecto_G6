# Datos locales

- `bronze/`: copias originales, separadas en `transactions/`, `credit/` y `complaints/`; los tres CSV iniciales usan Git LFS.
- `silver/`: salidas limpias y tipadas, generadas por código.
- `gold/`: marts y variables analíticas, generados por código.

Silver, Gold y otros archivos de datos permanecen excluidos de Git. Consulte el [inventario](../docs/datasets.md) para los nombres y huellas de los tres CSV iniciales. Para obtenerlos desde el remoto, instale Git LFS antes de clonar o ejecute `git lfs pull` después.
