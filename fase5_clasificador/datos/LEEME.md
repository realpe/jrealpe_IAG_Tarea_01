# Datos de la Fase 5

`bitext_es.parquet` **no se versiona** (6,9 MB). Descárgalo de
<https://huggingface.co/datasets/bitext/Bitext-customer-support-llm-chatbot-training-dataset>
en su edición en español y guárdalo en esta carpeta con ese nombre.
Licencia CDLA-Sharing-1.0: exige atribución y compartir igual.

| Archivo | Origen | Contenido |
| :--- | :--- | :--- |
| `bitext_es.parquet` | Corpus público | 24.184 ejemplos, 27 intenciones |
| `mapeo_intencion_carril.csv` | Decisión de diseño de este trabajo | 27 filas; se edita `carril_final` |
| `nucleo_duro_entrenamiento.jsonl` | Sintético | 24 casos de salud, legal, monto, reincidencia |
| `prueba.jsonl` | Sintético | 43 casos de medición; `revisado` marca los reescritos a mano |
| `canales_oficiales.json` | Ficticio | Directorio de áreas y canales de EcoMarket |
