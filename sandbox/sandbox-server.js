/**
 * Sandbox HTTP API Server
 *
 * Lightweight Express server running inside each Docker sandbox container.
 * The host backend communicates with this server via HTTP to execute commands,
 * manage files, and trigger Remotion renders — avoiding docker exec latency
 * and providing structured JSON responses.
 *
 * Endpoints:
 *   GET  /health              - Health check
 *   GET  /files?path=         - List files in directory
 *   GET  /file?path=          - Read file contents
 *   POST /file                - Write file (JSON body: { path, content })
 *   DELETE /file?path=        - Delete file
 *   POST /exec               - Execute shell command (JSON body: { command, timeout })
 *   POST /ffmpeg              - Run FFmpeg command (JSON body: { args, timeout })
 *   POST /remotion/render     - Render Remotion composition (JSON body: { timeline, output })
 *   GET  /assets?category=    - List available assets (memes, sfx, music)
 */

const express = require("express");
const { execSync, spawn } = require("child_process");
const fs = require("fs");
const path = require("path");

const app = express();
app.use(express.json({ limit: "50mb" }));

const WORKSPACE = "/workspace";

// Serve data directory (volume-mounted) as static files for Remotion
app.use("/static", express.static(path.join(WORKSPACE, "data")));
// Fallback: serve assets from workspace root if stored outside data/
app.use("/assets", express.static(path.join(WORKSPACE, "assets")));

// ─── Health ──────────────────────────────────────────────────────────

app.get("/health", (_req, res) => {
  res.json({ status: "ok", workspace: WORKSPACE });
});

// ─── Filesystem: List ────────────────────────────────────────────────

app.get("/files", (req, res) => {
  const dirPath = path.join(WORKSPACE, req.query.path || "");
  try {
    if (!fs.existsSync(dirPath)) {
      return res.status(404).json({ error: `Directory not found: ${dirPath}` });
    }
    const entries = fs.readdirSync(dirPath, { withFileTypes: true });
    const files = entries.map((e) => ({
      name: e.name,
      type: e.isDirectory() ? "directory" : "file",
      size: e.isFile() ? fs.statSync(path.join(dirPath, e.name)).size : null,
      modified: e.isFile()
        ? fs.statSync(path.join(dirPath, e.name)).mtime.toISOString()
        : null,
    }));
    res.json({ path: dirPath, files });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ─── Filesystem: Read ────────────────────────────────────────────────

app.get("/file", (req, res) => {
  const filePath = path.join(WORKSPACE, req.query.path || "");
  try {
    if (!fs.existsSync(filePath)) {
      return res.status(404).json({ error: `File not found: ${filePath}` });
    }
    const stat = fs.statSync(filePath);
    // Binary files: return base64
    const ext = path.extname(filePath).toLowerCase();
    const binaryExts = [".mp4", ".mp3", ".wav", ".png", ".jpg", ".gif", ".webp"];
    if (binaryExts.includes(ext)) {
      const data = fs.readFileSync(filePath);
      return res.json({
        path: filePath,
        size: stat.size,
        encoding: "base64",
        content: data.toString("base64"),
      });
    }
    const content = fs.readFileSync(filePath, "utf-8");
    res.json({ path: filePath, size: stat.size, encoding: "utf-8", content });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ─── Filesystem: Write ───────────────────────────────────────────────

app.post("/file", (req, res) => {
  const { path: filePath, content, encoding } = req.body;
  if (!filePath || content === undefined) {
    return res.status(400).json({ error: "Missing path or content" });
  }
  const fullPath = path.join(WORKSPACE, filePath);
  try {
    fs.mkdirSync(path.dirname(fullPath), { recursive: true });
    if (encoding === "base64") {
      fs.writeFileSync(fullPath, Buffer.from(content, "base64"));
    } else {
      fs.writeFileSync(fullPath, content, "utf-8");
    }
    const stat = fs.statSync(fullPath);
    res.json({ path: fullPath, size: stat.size, written: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ─── Filesystem: Delete ──────────────────────────────────────────────

app.delete("/file", (req, res) => {
  const filePath = path.join(WORKSPACE, req.query.path || "");
  try {
    if (!fs.existsSync(filePath)) {
      return res.status(404).json({ error: `File not found: ${filePath}` });
    }
    fs.unlinkSync(filePath);
    res.json({ deleted: true, path: filePath });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ─── Execution: Generic Command ──────────────────────────────────────

app.post("/exec", (req, res) => {
  const { command, timeout = 300 } = req.body;
  if (!command) {
    return res.status(400).json({ error: "Missing command" });
  }
  try {
    const stdout = execSync(command, {
      cwd: WORKSPACE,
      timeout: timeout * 1000,
      maxBuffer: 50 * 1024 * 1024, // 50MB
      encoding: "utf-8",
    });
    res.json({ exit_code: 0, stdout, stderr: "" });
  } catch (err) {
    res.json({
      exit_code: err.status || 1,
      stdout: err.stdout || "",
      stderr: err.stderr || err.message,
    });
  }
});

// ─── Execution: FFmpeg ───────────────────────────────────────────────

app.post("/ffmpeg", (req, res) => {
  const { args, timeout = 300 } = req.body;
  if (!args || !Array.isArray(args)) {
    return res.status(400).json({ error: "Missing args array" });
  }
  try {
    const cmd = `ffmpeg ${args.join(" ")}`;
    const stdout = execSync(cmd, {
      cwd: WORKSPACE,
      timeout: timeout * 1000,
      maxBuffer: 50 * 1024 * 1024,
      encoding: "utf-8",
    });
    res.json({ exit_code: 0, stdout, stderr: "" });
  } catch (err) {
    res.json({
      exit_code: err.status || 1,
      stdout: err.stdout || "",
      stderr: err.stderr || err.message,
    });
  }
});

// ─── Execution: Remotion Render (Node API) ──────────────────────────

// Cache the bundle so we don't re-bundle on every render
let _bundleLocation = null;

async function ensureBundle() {
  if (_bundleLocation) return _bundleLocation;
  const { bundle } = require("@remotion/bundler");
  _bundleLocation = await bundle({
    entryPoint: "/workspace/code/remotion-compositions/index.ts",
    onProgress: (pct) => {
      if (pct % 25 === 0) console.log(`Bundling: ${pct}%`);
    },
  });
  console.log("Remotion bundle ready:", _bundleLocation);
  return _bundleLocation;
}

app.post("/remotion/render", async (req, res) => {
  const { timeline, output = "/workspace/output/render.mp4" } = req.body;
  if (!timeline) {
    return res.status(400).json({ error: "Missing timeline JSON" });
  }

  // Write timeline for debugging
  const timelinePath = path.join(WORKSPACE, "intermediate/timeline/_current.json");
  fs.mkdirSync(path.dirname(timelinePath), { recursive: true });
  fs.writeFileSync(timelinePath, JSON.stringify(timeline, null, 2), "utf-8");

  // Ensure output directory exists
  fs.mkdirSync(path.dirname(output), { recursive: true });

  try {
    const { selectComposition, renderMedia } = require("@remotion/renderer");

    const bundleLocation = await ensureBundle();

    const browserExecutable = process.env.REMOTION_CHROME_EXECUTABLE || "/usr/bin/chromium";

    const chromiumOptions = {
      args: ["--disable-dev-shm-usage", "--no-sandbox", "--disable-gpu"],
    };

    // Resolve the composition with timeline as input props
    const composition = await selectComposition({
      serveUrl: bundleLocation,
      id: "TimelineComposition",
      inputProps: timeline,
      browserExecutable,
      chromiumOptions,
    });

    // Render the video
    await renderMedia({
      serveUrl: bundleLocation,
      composition,
      codec: "h264",
      outputLocation: output,
      inputProps: timeline,
      concurrency: 1,
      browserExecutable,
      chromiumOptions,
      onProgress: ({ progress }) => {
        if (Math.round(progress * 100) % 10 === 0) {
          console.log(`Render progress: ${Math.round(progress * 100)}%`);
        }
      },
    });

    const stat = fs.statSync(output);
    res.json({
      exit_code: 0,
      output_path: output,
      output_size: stat.size,
    });
  } catch (err) {
    console.error("Render error:", err);
    res.json({
      exit_code: 1,
      stdout: "",
      stderr: err.message || String(err),
    });
  }
});

// ─── Assets: List ────────────────────────────────────────────────────

app.get("/assets", (req, res) => {
  const category = req.query.category || "";
  const validCategories = ["memes", "sfx", "music"];
  if (!validCategories.includes(category)) {
    return res.status(400).json({
      error: `Invalid category. Must be one of: ${validCategories.join(", ")}`,
    });
  }
  const assetsDir = path.join(WORKSPACE, "assets", category);
  try {
    if (!fs.existsSync(assetsDir)) {
      return res.json({ category, assets: [] });
    }
    const files = fs.readdirSync(assetsDir);
    const assets = files.map((f) => {
      const stat = fs.statSync(path.join(assetsDir, f));
      return {
        name: f,
        path: `assets/${category}/${f}`,
        full_path: path.join(assetsDir, f),
        size: stat.size,
        ext: path.extname(f).toLowerCase(),
      };
    });
    res.json({ category, assets });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ─── Start Server ────────────────────────────────────────────────────

const PORT = process.env.SANDBOX_PORT || 9876;
app.listen(PORT, "0.0.0.0", () => {
  console.log(`Sandbox API listening on port ${PORT}`);
  console.log(`Workspace: ${WORKSPACE}`);
});
