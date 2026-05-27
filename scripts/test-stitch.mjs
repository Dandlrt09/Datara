import { stitch } from "@google/stitch-sdk";

const PROJECT_ID = "8302096542006595553";

async function main() {
  const project = stitch.project(PROJECT_ID);
  
  // Try minimal prompt first
  try {
    console.log("Attempting minimal generate...");
    const result = await project.generate("A simple dark sidebar with Upload, Chat, and Settings buttons");
    console.log("✅ Success!", result);
    console.log("ID:", result.id);
    
    try {
      const html = await result.getHtml();
      console.log("HTML URL:", html);
    } catch (e) {
      console.log("HTML error:", e.message);
    }
    
    try {
      const img = await result.getImage();
      console.log("Image URL:", img);
    } catch (e) {
      console.log("Image error:", e.message);
    }
  } catch (e) {
    console.error("❌ Failed:", e.message);
    console.error("Full error:", JSON.stringify(e, null, 2));
  }
}

main();
