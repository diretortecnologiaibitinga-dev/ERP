// Junta o build do modo "pagina" num HTML único (CSS e JS inline, React do cdnjs).
import { readFileSync, writeFileSync } from "node:fs";

const js = readFileSync("dist-pagina/app.js", "utf8").replaceAll("</script", "<\\/script");
const css = readFileSync("dist-pagina/app.css", "utf8");
const html = `<title>Estampa Produção</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700;800&family=Source+Sans+3:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap">
<style>${css}</style>
<div id="root"></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/react/18.3.1/umd/react.production.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/react-dom/18.3.1/umd/react-dom.production.min.js"></script>
<script>${js}</script>
`;
writeFileSync("dist-pagina/estampa.html", html);
console.log(`dist-pagina/estampa.html (${(html.length / 1024).toFixed(0)} KB)`);
