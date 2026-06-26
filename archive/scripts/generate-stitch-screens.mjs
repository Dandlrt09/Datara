import { stitch } from "@google/stitch-sdk";

const PROJECT_ID = "8302096542006595553";

const screens = [
  {
    name: "sidebar",
    prompt: "Create a DESKTOP sidebar navigation panel for a data analysis app called Datara. Dark theme with high contrast. Navigation buttons stacked vertically: Upload with upload icon, Chat with chat bubble icon, Dashboard with grid icon, Settings with gear icon. Below navigation show file count 'Archivos: 3' and message count 'Mensajes: 12' with small icons. List of active files below counts. Bottom of sidebar: 'Nueva Sesión' button. Use neon blue accent color. Clean professional data tool aesthetic.",
  },
  {
    name: "upload",
    prompt: "Create a DESKTOP file upload screen for a data analysis app called Datara. Dark theme. Large centered dropzone with dashed border and cloud upload icon. Text: 'Arrastra tu archivo aquí o haz clic para seleccionar'. Below: 'Soporta CSV, Excel, JSON, TSV'. Below dropzone: a table list of uploaded files showing filename, size, row count, and delete button per row. Clicking a file expands a preview table showing the first 10 rows. Modal dialog for duplicate file handling. Empty state when no files. Neon blue accent. Professional dark theme.",
  },
  {
    name: "chat",
    prompt: "Create a DESKTOP chat interface for a data analysis app called Datara. Dark theme. Top has title 'Análisis de Datos' and an export conversation download button. Main area is a scrollable chat message list. User messages: right-aligned blue bubbles with white text. AI responses: left-aligned dark cards with left neon blue accent border, containing text, optional chart placeholder, and optional data table. Each AI message has small export chart and export data buttons. Bottom: fixed text input field with send button. When no files loaded: friendly message 'Carga un archivo primero para empezar a analizar datos'. Neon blue accent.",
  },
  {
    name: "dashboard",
    prompt: "Create a DESKTOP analytics dashboard screen for a data analysis app called Datara. Dark theme. Top bar: 'Dashboard' title and a 'Limpiar Dashboard' clear button. Below: filter bar with dropdown column selector and multi-value selector. Horizontal row of KPI metric cards with label, large value number, and thin accent top border. Below KPIs: 2-column responsive grid of chart cards. Each card has a title, dark chart placeholder area, and small delete button. Empty state when no dashboard items exist. Neon blue accent. Professional analytics aesthetic.",
  },
  {
    name: "settings",
    prompt: "Create a DESKTOP settings/configuration screen for a data analysis app called Datara. Dark theme. Three cards stacked vertically. Card 1 'Configuración de IA': password input for API key with help text 'La clave se almacena en memoria durante la sesión', model dropdown selector, and 'Aplicar Cambios' accent button. Card 2 'Sesión': current session ID info and 'Nueva Sesión' reset button. Card 3 'Acerca de Datara': app name in neon blue, version, and description 'Plataforma de análisis de datos con inteligencia artificial'. Clean dark settings UI.",
  },
];

async function main() {
  const project = stitch.project(PROJECT_ID);
  const results = [];

  for (const screen of screens) {
    console.log(`\n🎨 Generating: ${screen.name}...`);
    try {
      // Don't pass options - SDK defaults to DESKTOP
      const result = await project.generate(screen.prompt);
      console.log(`✅ ${screen.name} generated! ID: ${result.id}`);

      let htmlUrl = null;
      let imageUrl = null;

      try { htmlUrl = await result.getHtml(); console.log(`   HTML URL available`); } 
      catch (e) { console.log(`   ⚠️ HTML: ${e.message}`); }

      try { imageUrl = await result.getImage(); console.log(`   Screenshot available`); } 
      catch (e) { console.log(`   ⚠️ Image: ${e.message}`); }

      results.push({
        name: screen.name,
        id: result.id,
        htmlUrl,
        imageUrl,
        data: result.data,
      });
    } catch (e) {
      console.error(`❌ ${screen.name} failed: ${e.message}`);
    }
  }

  console.log("\n" + "=".repeat(60));
  console.log("📋 SUMMARY");
  console.log("=".repeat(60));
  for (const r of results) {
    console.log(`\n${r.name}:`);
    console.log(`   Screen ID: ${r.id}`);
    console.log(`   Device: ${r.data?.deviceType || "N/A"}`);
    console.log(`   Status: ${r.data?.screenMetadata?.status || "N/A"}`);
    console.log(`   HTML: ${r.htmlUrl ? "✅ Available" : "❌ N/A"}`);
    console.log(`   Screenshot: ${r.imageUrl ? "✅ Available" : "❌ N/A"}`);
  }
  
  // Save results to a JSON file for later use
  const fs = await import("fs");
  fs.writeFileSync("scripts/stitch-results.json", JSON.stringify(results, null, 2));
  console.log("\n📄 Results saved to scripts/stitch-results.json");
  console.log("\n✅ Done!");
}

main().catch(console.error);
