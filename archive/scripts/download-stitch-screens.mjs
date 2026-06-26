import { stitch } from "@google/stitch-sdk";
import fs from "fs";
import path from "path";

const PROJECT_ID = "8302096542006595553";
const RESULTS_FILE = "scripts/stitch-results.json";
const OUTPUT_DIR = "frontend/screens";

// Ensure output directory exists
fs.mkdirSync(OUTPUT_DIR, { recursive: true });

async function fetchHTML(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return await response.text();
}

async function main() {
  const results = JSON.parse(fs.readFileSync(RESULTS_FILE, "utf-8"));
  const project = stitch.project(PROJECT_ID);

  for (const screen of results) {
    console.log(`\n📥 Fetching ${screen.name} HTML...`);
    
    try {
      // Get the screen by ID
      const screenObj = await project.screen(screen.id);
      
      // Get HTML URL
      const htmlUrl = await screenObj.getHtml();
      console.log(`   HTML URL: ${htmlUrl.substring(0, 80)}...`);
      
      // Download the HTML
      const html = await fetchHTML(htmlUrl);
      console.log(`   Downloaded: ${html.length} bytes`);
      
      // Save to file
      const filePath = path.join(OUTPUT_DIR, `${screen.name}.html`);
      fs.writeFileSync(filePath, html);
      console.log(`   Saved to: ${filePath}`);
      
      screen.localPath = filePath;
      screen.htmlSize = html.length;
    } catch (e) {
      console.error(`   ❌ Failed: ${e.message}`);
    }
  }

  // Update results with local paths
  fs.writeFileSync(RESULTS_FILE, JSON.stringify(results, null, 2));
  
  console.log("\n" + "=".repeat(60));
  console.log("📦 All screens downloaded to frontend/screens/");
  console.log("=".repeat(60));
  for (const r of results) {
    if (r.localPath) {
      console.log(`✅ ${r.name}: ${r.localPath} (${r.htmlSize} bytes)`);
    } else {
      console.log(`❌ ${r.name}: FAILED`);
    }
  }
}

main().catch(console.error);
