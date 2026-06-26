import { stitch } from "@google/stitch-sdk";

const PROJECT_ID = "8302096542006595553";

const prompts = {
  sidebar: "DESKTOP sidebar navigation for Datara data analysis app. PRIMARY COLOR #1A3FD4 deep royal blue. Background #0D1117, surface #161B22, text #F0F6FC. Fixed left sidebar full height. Top: brand area with 'Datara' in #1A3FD4. Nav buttons: Upload with cloud icon, Chat with message icon, Dashboard with grid icon, Settings with gear icon. Active button has left #1A3FD4 border. Status: 'Archivos: 3' and 'Mensajes: 12' with icons. Active file list. Bottom: 'Nueva Sesión' button with #1A3FD4 outline. Professional dark data tool aesthetic. The app name is always 'Datara' only, no suffixes.",
  
  upload: "DESKTOP file upload screen for Datara data app. PRIMARY COLOR #1A3FD4 deep blue. Dark theme #0D1117 bg, #161B22 surface, #F0F6FC text. Page title 'Subir Archivos'. Large centered dropzone with dashed #1A3FD4 border, cloud icon, text 'Arrastra tu archivo aquí o haz clic para seleccionar'. Below: 'Soporta CSV, Excel, JSON, TSV'. File list table with filename, size, rows, sheet selector, delete button. Expandable preview rows. Duplicate file dialog. Empty state message. No sidebar - main content only. App name: Datara only.",
  
  chat: "DESKTOP chat interface for Datara data app. PRIMARY COLOR #1A3FD4 deep blue. Dark theme #0D1117 bg, #161B22 surface. Top bar: 'Análisis de Datos' title and export button. Scrollable messages: user messages right-aligned #1A3FD4 bubble white text. AI messages left-aligned dark card with 4px left #1A3FD4 border, includes text, chart placeholder, data table. Small export buttons per message. Bottom fixed input with send button. Empty state: 'Carga un archivo primero'. No sidebar - main content only. App name: Datara only.",
  
  dashboard: "DESKTOP analytics dashboard for Datara data app. PRIMARY COLOR #1A3FD4 deep blue. Dark theme #0D1117 bg, #161B22 surface. Top bar: 'Dashboard' title and 'Limpiar Dashboard' button. Filter bar with column dropdown and multi-select. KPI row: 4 metric cards with thin #1A3FD4 top border. Chart grid: 2-column cards with title, dark chart area, delete button. Empty state: 'No hay widgets en el dashboard'. No sidebar - main content only. App name: Datara only.",
  
  settings: "DESKTOP settings screen for Datara data app. PRIMARY COLOR #1A3FD4 deep blue. Dark theme #0D1117 bg, #161B22 surface. Three cards: Card 1 'Configuración de IA' with password input for API key, help text, model dropdown, 'Aplicar Cambios' #1A3FD4 button. Card 2 'Sesión' with session ID and 'Nueva Sesión' reset button. Card 3 'Acerca de Datara' with app name in #1A3FD4, version, description 'Plataforma de análisis de datos con inteligencia artificial'. No sidebar - main content only. App name: Datara only.",
};

async function main() {
  const project = stitch.project(PROJECT_ID);
  const results = [];

  for (const [name, prompt] of Object.entries(prompts)) {
    console.log(`🎨 Generating ${name}...`);
    try {
      const result = await project.generate(prompt);
      console.log(`✅ ${name} generated! ID: ${result.id}`);
      
      let htmlUrl = null, imageUrl = null;
      try { htmlUrl = await result.getHtml(); } catch (e) { console.log(`   ⚠️ HTML: ${e.message}`); }
      try { imageUrl = await result.getImage(); } catch (e) { console.log(`   ⚠️ Image: ${e.message}`); }
      
      results.push({ name, id: result.id, htmlUrl, imageUrl, data: result.data });
      console.log(`   Done.`);
    } catch (e) {
      console.error(`❌ ${name} failed: ${e.message}`);
    }
  }
  
  const fs = await import("fs");
  fs.writeFileSync("scripts/stitch-results-v2.json", JSON.stringify(results, null, 2));
  console.log("\n✅ Complete! Results saved to scripts/stitch-results-v2.json");
}

main().catch(console.error);
