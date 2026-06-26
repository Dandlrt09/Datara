import { stitch } from "@google/stitch-sdk";

const PROJECT_ID = "8302096542006595553";

async function main() {
  const project = stitch.project(PROJECT_ID);
  
  // Test DESKTOP explicitly
  try {
    console.log("Testing DESKTOP deviceType...");
    const result = await project.generate("A dark desktop login page", { deviceType: "DESKTOP" });
    console.log("✅ DESKTOP worked!", result.id, "deviceType:", result.data?.deviceType);
  } catch (e) {
    console.error("❌ DESKTOP failed:", e.message);
  }

  // Test without deviceType (default)
  try {
    console.log("\nTesting default (no deviceType)...");
    const result = await project.generate("A dark desktop login page");
    console.log("✅ Default worked!", result.id, "deviceType:", result.data?.deviceType);
  } catch (e) {
    console.error("❌ Default failed:", e.message);
  }

  // Test TABLET
  try {
    console.log("\nTesting TABLET...");
    const result = await project.generate("A dark login page", { deviceType: "TABLET" });
    console.log("✅ TABLET worked!", result.id);
  } catch (e) {
    console.error("❌ TABLET failed:", e.message);
  }
}

main().catch(console.error);
