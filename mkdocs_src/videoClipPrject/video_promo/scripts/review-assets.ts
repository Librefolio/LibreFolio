import fs from "node:fs";
import path from "node:path";
import { execSync } from "node:child_process";
import { videoPlan } from "../src/config/videoPlan";

const VIDEO_PROMO = process.cwd();
const AI_DIR = path.resolve(VIDEO_PROMO, "public/ai");
const OUT_DIR = path.resolve(VIDEO_PROMO, "out");
const BUNDLE_DIR = path.resolve(OUT_DIR, "review_bundle");

const manifest = {
  generatedAt: new Date().toISOString(),
  projectRoot: VIDEO_PROMO,
  aiAssetsFound: [] as string[],
  audioFilesFound: [] as string[],
  videoFound: false,
  metadata: {} as any,
  outputs: [] as string[],
  warnings: [] as string[],
  errors: [] as string[],
};

function ensureDir(dir: string): void {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

function runCommand(command: string): string {
  try {
    return execSync(command, { encoding: "utf8" });
  } catch (e: any) {
    manifest.errors.push(`Command failed: ${command}\nError: ${e.message}`);
    console.error(`❌ Failed: ${command}`);
    return "";
  }
}

function collectAiAssets(): void {
  console.log("🔍 Collecting AI assets inventory...");
  if (!fs.existsSync(AI_DIR)) {
    manifest.warnings.push(`AI dir not found: ${AI_DIR}`);
    return;
  }

  const files = fs.readdirSync(AI_DIR);
  let inventoryStr = "";

  for (const f of files) {
    const fullPath = path.join(AI_DIR, f);
    if (fs.statSync(fullPath).isFile()) {
      manifest.aiAssetsFound.push(f);
      inventoryStr += `----------------------------------------\nFILE: ${f}\n`;
      const info = runCommand(`file "${fullPath}"`).trim();
      inventoryStr += `${info}\n\n`;
    }
  }

  const outPath = path.join(BUNDLE_DIR, "ai_assets_inventory.txt");
  fs.writeFileSync(outPath, inventoryStr);
  manifest.outputs.push("ai_assets_inventory.txt");
}

function collectAudioDurations(): void {
  console.log("⏱️ Collecting audio durations...");
  const audioFiles = manifest.aiAssetsFound.filter((f) => f.endsWith(".mp3") || f.endsWith(".wav"));
  manifest.audioFilesFound = audioFiles;

  let durationsStr = "";
  for (const name of audioFiles) {
    const fullPath = path.join(AI_DIR, name);
    const durStr = runCommand(`ffprobe -i "${fullPath}" -show_entries format=duration -v quiet -of csv="p=0"`).trim();
    durationsStr += `${name}: ${durStr}s\n`;
  }

  const outPath = path.join(BUNDLE_DIR, "ai_audio_durations.txt");
  fs.writeFileSync(outPath, durationsStr);
  manifest.outputs.push("ai_audio_durations.txt");
}

function generateWaveforms(): void {
  console.log("🌊 Generating audio waveforms...");
  const waveDir = path.join(BUNDLE_DIR, "ai_waveforms");
  ensureDir(waveDir);

  for (const name of manifest.audioFilesFound) {
    const fullPath = path.join(AI_DIR, name);
    const outPath = path.join(waveDir, `${name}.png`);
    runCommand(
      `ffmpeg -y -i "${fullPath}" -filter_complex "aformat=channel_layouts=mono,showwavespic=s=1200x300:colors=white" -frames:v 1 "${outPath}" -loglevel error`
    );
    manifest.outputs.push(`ai_waveforms/${name}.png`);
  }
}

function generateSpectrums(): void {
  console.log("🌈 Generating audio spectrums...");
  const specDir = path.join(BUNDLE_DIR, "ai_spectrums");
  ensureDir(specDir);

  for (const name of manifest.audioFilesFound) {
    const fullPath = path.join(AI_DIR, name);
    const outPath = path.join(specDir, `${name}.png`);
    runCommand(
      `ffmpeg -y -i "${fullPath}" -lavfi "showspectrumpic=s=1200x400:legend=disabled:color=intensity" -frames:v 1 "${outPath}" -loglevel error`
    );
    manifest.outputs.push(`ai_spectrums/${name}.png`);
  }
}

function getVideoMetadata(videoPath: string) {
  const durationStr = runCommand(`ffprobe -v error -select_streams v:0 -show_entries stream=duration -of default=noprint_wrappers=1:nokey=1 "${videoPath}"`).trim();
  const fpsStr = runCommand(`ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of default=noprint_wrappers=1:nokey=1 "${videoPath}"`).trim();
  const resStr = runCommand(`ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0:s=x "${videoPath}"`).trim();
  
  let fps = 30;
  if (fpsStr.includes('/')) {
    const [num, den] = fpsStr.split('/');
    fps = Math.round(Number(num) / Number(den));
  } else if (Number(fpsStr)) {
    fps = Number(fpsStr);
  }

  return { durationSec: Number(durationStr) || 0, fps, resolution: resStr || "unknown" };
}

function getSceneBoundaries() {
  const scenes = Object.entries(videoPlan.scenes);
  let currentFrame = 0;
  const boundaries = [];
  const packets = [];
  
  for (let i = 0; i < scenes.length; i++) {
    const [name, config] = scenes[i];
    const dur = config.durationInFrames;
    const start = currentFrame;
    const end = currentFrame + dur;
    
    packets.push({
      name,
      frames: [
        start,
        Math.floor(start + dur * 0.25),
        Math.floor(start + dur * 0.5),
        Math.floor(start + dur * 0.75),
        Math.max(start, end - 1),
      ]
    });

    if (i < scenes.length - 1) {
      const boundary = end;
      boundaries.push({
        name: `${name}_to_${scenes[i+1][0]}`,
        boundary,
        frames: [boundary - 12, boundary - 8, boundary - 4, boundary, boundary + 4, boundary + 8, boundary + 12]
      });
    }

    currentFrame = end;
  }
  
  return { packets, boundaries };
}

function generateVideoReviewAssets(): void {
  console.log("🎬 Generating video review assets...");

  if (!fs.existsSync(OUT_DIR)) {
    manifest.warnings.push(`Output dir not found: ${OUT_DIR}`);
    return;
  }

  const files = fs.readdirSync(OUT_DIR);
  let targetVideo = files.find((f) => f === "librefolio_promo_en.mp4");
  if (!targetVideo) {
    targetVideo = files.find((f) => f.endsWith(".mp4") && !f.includes("_preview"));
  }

  if (!targetVideo) {
    manifest.warnings.push(`No compiled .mp4 video found in ${OUT_DIR}`);
    return;
  }

  manifest.videoFound = true;
  const videoPath = path.join(OUT_DIR, targetVideo);
  const baseName = path.parse(targetVideo).name;
  const vidOutDir = path.join(BUNDLE_DIR, "video");
  ensureDir(vidOutDir);

  const meta = getVideoMetadata(videoPath);
  manifest.metadata = {
    file: targetVideo,
    durationSec: meta.durationSec,
    fps: meta.fps,
    resolution: meta.resolution,
    framesGenerated: {
      contactSheets: 0,
      keyframes: 0,
      scenePackets: 0,
      transitions: 0
    }
  };

  // Legacy Contact sheet (1fps)
  const contactSheet1fps = path.join(vidOutDir, `${baseName}_contact_sheet_1fps.jpg`);
  runCommand(`ffmpeg -y -i "${videoPath}" -vf "fps=1,scale=480:-1,tile=8x5" -frames:v 1 "${contactSheet1fps}" -loglevel error`);
  manifest.outputs.push(`video/${baseName}_contact_sheet_1fps.jpg`);
  manifest.metadata.framesGenerated.contactSheets++;

  // Dense Contact sheet (2fps)
  console.log("   📸 Creating dense contact sheet (2fps)...");
  const contactSheet2fps = path.join(vidOutDir, `${baseName}_contact_sheet_2fps.jpg`);
  runCommand(`ffmpeg -y -i "${videoPath}" -vf "fps=2,scale=360:-1,tile=12x9" -frames:v 1 "${contactSheet2fps}" -loglevel error`);
  manifest.outputs.push(`video/${baseName}_contact_sheet_2fps.jpg`);
  manifest.metadata.framesGenerated.contactSheets++;

  // Generate keyframes based on mid points of scenes
  const { packets, boundaries } = getSceneBoundaries();

  // Scene Packets
  console.log("   🎞️ Extracting scene packets...");
  const packetsDir = path.join(vidOutDir, "scene_packets");
  ensureDir(packetsDir);
  for (const scene of packets) {
    const sceneDir = path.join(packetsDir, scene.name);
    ensureDir(sceneDir);
    const filter = scene.frames.map(f => `eq(n,${f})`).join('+');
    runCommand(`ffmpeg -y -i "${videoPath}" -vf "select='${filter}',scale=960:-1" -vsync vfr "${path.join(sceneDir, "frame_%02d.jpg")}" -loglevel error`);
    
    // Rename them nicely
    const extracted = fs.readdirSync(sceneDir).filter(f => f.endsWith('.jpg')).sort();
    const names = ["01_start", "02_25pct", "03_mid", "04_75pct", "05_end"];
    extracted.forEach((file, idx) => {
      if (names[idx]) {
        fs.renameSync(path.join(sceneDir, file), path.join(sceneDir, `frame_${names[idx]}.jpg`));
        manifest.outputs.push(`video/scene_packets/${scene.name}/frame_${names[idx]}.jpg`);
        manifest.metadata.framesGenerated.scenePackets++;
      }
    });
  }

  // Transitions
  console.log("   🔄 Extracting transition boundaries...");
  const transDir = path.join(vidOutDir, "transitions");
  ensureDir(transDir);
  for (const trans of boundaries) {
    const tDir = path.join(transDir, trans.name);
    ensureDir(tDir);
    const filter = trans.frames.map(f => `eq(n,${f})`).join('+');
    runCommand(`ffmpeg -y -i "${videoPath}" -vf "select='${filter}',scale=960:-1" -vsync vfr "${path.join(tDir, "frame_offset_%02d.jpg")}" -loglevel error`);
    manifest.outputs.push(`video/transitions/${trans.name}/frame_offset_*.jpg`);
    
    const count = fs.readdirSync(tDir).filter(f => f.endsWith('.jpg')).length;
    manifest.metadata.framesGenerated.transitions += count;
  }

  // Preview video
  console.log("   🗜️ Encoding lightweight preview video...");
  const previewOut = path.join(vidOutDir, `${baseName}_preview.mp4`);
  runCommand(
    `ffmpeg -y -i "${videoPath}" -vf "scale=1280:-2" -c:v libx264 -crf 28 -preset veryfast -c:a aac -b:a 96k "${previewOut}" -loglevel error`
  );
  manifest.outputs.push(`video/${baseName}_preview.mp4`);
}

function writeManifest(): void {
  const manifestPath = path.join(BUNDLE_DIR, "manifest.json");
  fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));
  console.log(`\n✅ Review bundle generated at: ${BUNDLE_DIR}`);
  if (manifest.errors.length > 0) {
    console.log(`⚠️ Encountered ${manifest.errors.length} errors during execution.`);
  }
}

function main() {
  const args = process.argv.slice(2);
  if (args.includes("--clean")) {
    if (fs.existsSync(BUNDLE_DIR)) {
      console.log("🧹 Cleaning old review bundle...");
      fs.rmSync(BUNDLE_DIR, { recursive: true, force: true });
    }
  }

  ensureDir(BUNDLE_DIR);

  collectAiAssets();
  collectAudioDurations();
  generateWaveforms();
  generateSpectrums();
  generateVideoReviewAssets();
  writeManifest();
}

main();
