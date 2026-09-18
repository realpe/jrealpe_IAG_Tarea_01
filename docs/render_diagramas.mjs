/**
 * Regenera los PNG de los diagramas a partir del codigo Mermaid embebido en los .md
 *
 * Por que existe este script: los diagramas usan el motor de layout ELK
 * (`layout: elk`), que produce lineas en angulo recto y ancla las flechas en los
 * vertices de los nodos. ELK es un paquete opcional de Mermaid y no esta garantizado
 * en todos los renderizadores (GitHub, por ejemplo, no lo documenta), asi que el
 * repositorio guarda tambien la imagen ya renderizada. El codigo Mermaid sigue siendo
 * la fuente de verdad; la imagen es solo su render reproducible.
 *
 * Uso:
 *   npm install mermaid @mermaid-js/layout-elk playwright --legacy-peer-deps
 *   npx playwright install chromium
 *   npx http-server . -p 8899        # o: python3 -m http.server 8899
 *   node docs/render_diagramas.mjs
 */

import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

const RAIZ = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const PUERTO = 8899;

// Cada entrada: archivo markdown de origen -> PNG de destino
const DIAGRAMAS = [
  { md: 'README.md', png: 'docs/arquitectura.png' },
  { md: 'fase1_seleccion_modelo.md', png: 'docs/arquitectura-fase1.png' },
  { md: 'fase4_viabilidad_rag.md', png: 'docs/rag-ingesta.png', indice: 0 },
  { md: 'fase4_viabilidad_rag.md', png: 'docs/rag-consulta.png', indice: 1 },
];

// Extrae el bloque ```mermaid numero `indice` (0 por defecto) de un archivo markdown
function extraerMermaid(rutaMd, indice = 0) {
  const texto = fs.readFileSync(path.join(RAIZ, rutaMd), 'utf8');
  const bloques = [...texto.matchAll(/```mermaid\n([\s\S]*?)```/g)];
  if (!bloques[indice]) throw new Error(`No hay bloque mermaid ${indice} en ${rutaMd}`);
  return bloques[indice][1];
}

const PAGINA = `<!doctype html><html><head><meta charset="utf-8">
<style>body{margin:0;background:#f7f7f7;font-family:system-ui}#c{padding:20px}</style></head>
<body><div id="c"></div>
<script type="module">
import mermaid from './node_modules/mermaid/dist/mermaid.esm.min.mjs';
import elk from './node_modules/@mermaid-js/layout-elk/dist/mermaid-layout-elk.esm.min.mjs';
mermaid.registerLayoutLoaders(elk);
mermaid.initialize({ startOnLoad: false, theme: 'default' });
window.dibujar = async (txt) => {
  const { svg } = await mermaid.render('g' + Date.now(), txt);
  document.getElementById('c').innerHTML = svg;
  const el = document.querySelector('#c svg');
  // Quitar el alto fijo deja que el SVG se mida por su contenido real
  el.removeAttribute('height'); el.style.maxWidth = 'none';
  const bb = el.getBBox();
  return { w: Math.ceil(bb.width), h: Math.ceil(bb.height) };
};
window.listo = true;
</script></body></html>`;

fs.writeFileSync(path.join(RAIZ, '_render.html'), PAGINA);

// deviceScaleFactor 2 => PNG al doble de resolucion, legible al hacer zoom en GitHub
const navegador = await chromium.launch();
const pagina = await navegador.newPage({ viewport: { width: 1600, height: 1200 }, deviceScaleFactor: 2 });

for (const { md, png, indice } of DIAGRAMAS) {
  await pagina.goto(`http://localhost:${PUERTO}/_render.html`);
  await pagina.waitForFunction('window.listo === true');
  const dim = await pagina.evaluate((t) => window.dibujar(t), extraerMermaid(md, indice ?? 0));
  await pagina.setViewportSize({ width: dim.w + 60, height: dim.h + 60 });
  await pagina.locator('#c svg').screenshot({ path: path.join(RAIZ, png) });
  console.log(`${png}  <-  ${md}   (${dim.w}x${dim.h})`);
}

await navegador.close();
fs.unlinkSync(path.join(RAIZ, '_render.html'));
