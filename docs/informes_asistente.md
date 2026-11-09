# Informes del asistente

Los PDF los dibuja ReportLab en el servidor (`app/modules/reports/assistant_pdf.py`).

No se usa un navegador ni ECharts para el archivo. La polilínea y la tabla salen de la misma lista de puntos que la pantalla pide a `/api/asistente/graficos/{id}`: primero se agregan las lecturas y después se dibujan. Así el gráfico del PDF y el de la pantalla no se calculan por caminos distintos.

El pie de cada hoja lleva el periodo, «Datos hasta», si el origen es histórico o en vivo, la fecha de generación y la persona que lo pidió.
