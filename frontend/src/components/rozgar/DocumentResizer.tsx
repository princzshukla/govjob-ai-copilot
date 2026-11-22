import { useEffect, useRef, useState } from "react";
import {
  Download,
  FileUp,
  Loader2,
  RefreshCw,
  Sparkles,
  ZoomIn,
} from "lucide-react";
import { PageShell } from "../../views/directions/rozgar-pages";
import { PRESETS, toolFaqs } from "../../lib/specs";

interface OutputImage {
  url: string;
  sizeKB: number;
  width: number;
  height: number;
  blob: Blob;
}

const input =
  "h-11 w-full rounded-lg border-2 border-line bg-white px-3 text-base text-ink outline-none placeholder:text-ink/45 focus:border-saffron sm:text-[14px]";
const smallInput =
  "min-h-11 w-full rounded-md border-2 border-line bg-white px-2 text-base text-ink outline-none placeholder:text-ink/45 focus:border-saffron sm:h-8 sm:text-[12px]";
const label = "mb-1 block text-[10.5px] font-bold tracking-[.14em] text-ink/50 uppercase";
const range = "w-full accent-saffron cursor-pointer";

function Chip({ children, tone = "cream" }: { children: React.ReactNode; tone?: "cream" | "green" | "saffron" }) {
  const cls =
    tone === "green"
      ? "bg-govgreen/15 text-govgreen"
      : tone === "saffron"
        ? "bg-saffron/20 text-saffron"
        : "bg-cream text-ink/75";
  return <span className={`rounded px-2 py-1 text-[12.5px] font-semibold ${cls}`}>{children}</span>;
}

function ToolPanel({ children }: { children: React.ReactNode }) {
  return <div className="rounded-lg border border-line bg-cream/40 p-3">{children}</div>;
}

export function DocumentResizer() {
  const [presetIdx, setPresetIdx] = useState(0);
  const [customWidth, setCustomWidth] = useState("350");
  const [customHeight, setCustomHeight] = useState("450");
  const [customMaxKB, setCustomMaxKB] = useState("50");

  const [srcUrl, setSrcUrl] = useState<string | null>(null);
  const [srcInfo, setSrcInfo] = useState<{
    name: string;
    width: number;
    height: number;
    sizeKB: number;
  } | null>(null);

  const [zoom, setZoom] = useState(1);
  const [panX, setPanX] = useState(0);
  const [panY, setPanY] = useState(0);
  const [cleanSignature, setCleanSignature] = useState(true);
  const [addNameDate, setAddNameDate] = useState(false);
  const [candidateName, setCandidateName] = useState("");
  const [photoDate, setPhotoDate] = useState(() => new Date().toISOString().split("T")[0]);

  const [output, setOutput] = useState<OutputImage | null>(null);
  const [processing, setProcessing] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const preset = PRESETS[presetIdx]!;
  const targetWidth = preset.width || Math.max(1, parseInt(customWidth, 10) || 300);
  const targetHeight = preset.height || Math.max(1, parseInt(customHeight, 10) || 300);
  const maxKB = preset.type === "custom" ? parseInt(customMaxKB, 10) || 50 : preset.maxKB;
  const minKB = preset.minKB;

  const compressToTarget = async (
    canvas: HTMLCanvasElement,
  ): Promise<{ blob: Blob; url: string; sizeKB: number }> => {
    let low = 0.05;
    let high = 0.98;
    let bestBlob: Blob | null = null;
    const minBytes = minKB * 1024;
    const maxBytes = maxKB * 1024;

    for (let i = 0; i < 8; i++) {
      const mid = (low + high) / 2;
      const b = await new Promise<Blob>((res) =>
        canvas.toBlob((blob) => res(blob!), "image/jpeg", mid),
      );
      bestBlob = b;

      if (b.size >= minBytes && b.size <= maxBytes) break;
      if (b.size > maxBytes) {
        high = mid;
      } else {
        low = mid;
      }
    }

    if (bestBlob && bestBlob.size > maxBytes && canvas.width > 120) {
      const fallback = document.createElement("canvas");
      fallback.width = Math.round(canvas.width * 0.9);
      fallback.height = Math.round(canvas.height * 0.9);
      const fctx = fallback.getContext("2d")!;
      fctx.drawImage(canvas, 0, 0, fallback.width, fallback.height);
      return compressToTarget(fallback);
    }

    const finalBlob = bestBlob!;
    return {
      blob: finalBlob,
      url: URL.createObjectURL(finalBlob),
      sizeKB: Math.round((finalBlob.size / 1024) * 10) / 10,
    };
  };

  const process = async () => {
    if (!srcUrl || !targetWidth || !targetHeight) return;
    setProcessing(true);

    try {
      const img = await new Promise<HTMLImageElement>((resolve, reject) => {
        const image = new Image();
        image.onload = () => resolve(image);
        image.onerror = reject;
        image.src = srcUrl;
      });

      const canvas = canvasRef.current || document.createElement("canvas");
      canvas.width = targetWidth;
      canvas.height = targetHeight;
      const ctx = canvas.getContext("2d", { willReadFrequently: true });
      if (!ctx) throw new Error("Canvas unavailable");

      ctx.fillStyle = "#FFFFFF";
      ctx.fillRect(0, 0, targetWidth, targetHeight);
      ctx.imageSmoothingEnabled = true;
      ctx.imageSmoothingQuality = "high";

      const srcAspect = img.width / img.height;
      const dstAspect = targetWidth / targetHeight;
      let baseW = img.width;
      let baseH = img.height;

      if (srcAspect > dstAspect) {
        baseW = img.height * dstAspect;
      } else {
        baseH = img.width / dstAspect;
      }

      const drawW = baseW / zoom;
      const drawH = baseH / zoom;
      const maxPanX = (img.width - drawW) / 2;
      const maxPanY = (img.height - drawH) / 2;

      const cropX = Math.max(0, Math.min(img.width - drawW, (img.width - drawW) / 2 + panX * maxPanX));
      const cropY = Math.max(0, Math.min(img.height - drawH, (img.height - drawH) / 2 + panY * maxPanY));

      ctx.drawImage(img, cropX, cropY, drawW, drawH, 0, 0, targetWidth, targetHeight);

      // Adaptive binarization for signatures — yellow/gray paper → crisp white, ink darkened
      if (preset.type === "signature" && cleanSignature) {
        const imgData = ctx.getImageData(0, 0, targetWidth, targetHeight);
        const d = imgData.data;
        for (let i = 0; i < d.length; i += 4) {
          const lum = 0.299 * d[i]! + 0.587 * d[i + 1]! + 0.114 * d[i + 2]!;
          if (lum > 165) {
            d[i] = 255;
            d[i + 1] = 255;
            d[i + 2] = 255;
          } else {
            const factor = lum / 165;
            d[i] = d[i]! * factor * 0.45;
            d[i + 1] = d[i + 1]! * factor * 0.45;
            d[i + 2] = d[i + 2]! * factor * 0.45;
          }
        }
        ctx.putImageData(imgData, 0, 0);
      }

      // Candidate name & date strip (photos only)
      if (preset.type === "photo" && addNameDate && (candidateName || photoDate)) {
        const stripHeight = Math.round(targetHeight * 0.17);
        const stripY = targetHeight - stripHeight;

        ctx.fillStyle = "#FFFFFF";
        ctx.fillRect(0, stripY, targetWidth, stripHeight);
        ctx.strokeStyle = "#D1D5DB";
        ctx.lineWidth = 1;
        ctx.strokeRect(0, stripY, targetWidth, stripHeight);

        ctx.fillStyle = "#000000";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";

        if (candidateName && photoDate) {
          ctx.font = `bold ${Math.round(stripHeight * 0.35)}px sans-serif`;
          ctx.fillText(candidateName.toUpperCase(), targetWidth / 2, stripY + stripHeight * 0.35);
          ctx.font = `600 ${Math.round(stripHeight * 0.3)}px sans-serif`;
          ctx.fillText(photoDate, targetWidth / 2, stripY + stripHeight * 0.75);
        } else {
          ctx.font = `bold ${Math.round(stripHeight * 0.4)}px sans-serif`;
          ctx.fillText(
            (candidateName || photoDate || "").toUpperCase(),
            targetWidth / 2,
            stripY + stripHeight / 2,
          );
        }
      }

      const result = await compressToTarget(canvas);

      setOutput({
        url: result.url,
        sizeKB: result.sizeKB,
        width: targetWidth,
        height: targetHeight,
        blob: result.blob,
      });
    } finally {
      setProcessing(false);
    }
  };

  useEffect(() => {
    if (srcUrl) void process();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    presetIdx,
    customWidth,
    customHeight,
    customMaxKB,
    srcUrl,
    zoom,
    panX,
    panY,
    cleanSignature,
    addNameDate,
    candidateName,
    photoDate,
  ]);

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!/^image\//.test(file.type)) {
      e.target.value = "";
      return;
    }
    const url = URL.createObjectURL(file);
    setSrcUrl(url);
    setOutput(null);
    setZoom(1);
    setPanX(0);
    setPanY(0);

    const probe = new Image();
    probe.onload = () =>
      setSrcInfo({
        name: file.name,
        width: probe.width,
        height: probe.height,
        sizeKB: Math.round((file.size / 1024) * 10) / 10,
      });
    probe.src = url;
  };

  const download = () => {
    if (!output) return;
    const a = document.createElement("a");
    a.href = output.url;
    a.download = `${preset.label.split(" ")[0]!.toLowerCase()}-${output.width}x${output.height}.jpg`;
    a.click();
  };

  const isCompliant = output ? output.sizeKB >= minKB && output.sizeKB <= maxKB : false;

  return (
    <PageShell
      kicker="Photo & Signature"
      title="Government photo & signature resizer"
      subtitle="Crop, resize, clean and compress to each exam board's exact limits — processed entirely in your browser."
    >
      {/* preset + dimensions */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <div>
          <label className={label} htmlFor="preset">Exam board preset</label>
          <select
            id="preset"
            value={String(presetIdx)}
            onChange={(e) => setPresetIdx(Number(e.target.value))}
            className={input}
          >
            {PRESETS.map((p, i) => (
              <option key={p.label} value={String(i)}>
                {p.label}
              </option>
            ))}
          </select>
        </div>

        {preset.type === "custom" ? (
          <>
            <div>
              <label className={label} htmlFor="custom-w">Width × Height (px)</label>
              <div className="flex gap-2">
                <input id="custom-w" type="number" min={1} value={customWidth} onChange={(e) => setCustomWidth(e.target.value)} placeholder="W" className={input} />
                <input type="number" min={1} value={customHeight} onChange={(e) => setCustomHeight(e.target.value)} placeholder="H" className={input} aria-label="Height in pixels" />
              </div>
            </div>
            <div>
              <label className={label} htmlFor="custom-kb">Max file size (KB)</label>
              <input id="custom-kb" type="number" min={5} value={customMaxKB} onChange={(e) => setCustomMaxKB(e.target.value)} className={input} />
            </div>
          </>
        ) : (
          <div className="lg:col-span-2">
            <span className={label}>Statutory requirements</span>
            <div className="flex flex-wrap items-center gap-1.5">
              <Chip>{preset.width} × {preset.height} px</Chip>
              <Chip>{preset.minKB}–{preset.maxKB} KB · JPEG</Chip>
              <Chip tone={preset.type === "photo" ? "green" : "saffron"}>
                {preset.type === "photo" ? "Passport Photo" : "Signature"}
              </Chip>
            </div>
          </div>
        )}
      </div>

      {/* dropzone */}
      {!srcUrl && (
        <div className="mt-4">
          <label
            className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed border-line-strong bg-cream/40 px-6 py-12 text-center transition-colors hover:border-saffron ${
              processing ? "pointer-events-none opacity-70" : ""
            }`}
          >
            {processing ? (
              <Loader2 className="size-8 animate-spin text-saffron" />
            ) : (
              <FileUp className="size-8 text-ink/40" />
            )}
            <span className="text-[15px] font-semibold text-ink">Click to select a photo or signature image</span>
            <span className="text-[12.5px] text-ink/55">JPG, PNG or WEBP — auto-converts to portal-compliant JPEG</span>
            <input type="file" accept="image/*" className="sr-only" onChange={handleFile} />
          </label>
          <label
            className={`mt-2 flex min-h-11 cursor-pointer items-center justify-center gap-2 rounded-lg border-2 border-line bg-white text-[14px] font-bold text-ink ${
              processing ? "pointer-events-none opacity-70" : ""
            }`}
          >
            Take photo with camera
            <input type="file" accept="image/*" capture="environment" className="sr-only" onChange={handleFile} />
          </label>
        </div>
      )}

      {/* workspace */}
      {srcUrl && (
        <div className="mt-4 space-y-4 rounded-lg border border-line bg-white p-4">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line pb-3">
            <div className="flex min-w-0 items-center gap-2">
              <span className="max-w-[220px] truncate text-[13px] font-semibold text-ink sm:max-w-none">
                {srcInfo?.name}
              </span>
              {srcInfo && (
                <span className="text-[12px] tabular-nums text-ink/55">
                  {srcInfo.width}×{srcInfo.height} px · {srcInfo.sizeKB} KB
                </span>
              )}
            </div>
            <label className="flex min-h-11 shrink-0 cursor-pointer items-center text-[13px] font-bold text-saffron hover:underline">
              Replace file
              <input type="file" accept="image/*" className="sr-only" onChange={handleFile} />
            </label>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {/* zoom + pan */}
            <ToolPanel>
              <div className="flex items-center justify-between">
                <label className="flex items-center gap-1.5 text-[12px] font-bold text-ink">
                  <ZoomIn className="size-3.5 text-saffron" /> Zoom ({zoom.toFixed(1)}×)
                </label>
                <button
                  className="flex items-center gap-1 rounded-md px-1.5 py-1 text-[11px] font-semibold text-ink/55 hover:text-ink"
                  onClick={() => {
                    setZoom(1);
                    setPanX(0);
                    setPanY(0);
                  }}
                >
                  <RefreshCw className="size-3" /> Reset
                </button>
              </div>
              <input type="range" min="1" max="2.5" step="0.05" value={zoom} onChange={(e) => setZoom(parseFloat(e.target.value))} className={`mt-2 ${range}`} aria-label="Zoom" />
              {zoom > 1 && (
                <div className="grid grid-cols-2 gap-2 pt-2 text-[11px] text-ink/60">
                  <label>
                    Pan X
                    <input type="range" min="-1" max="1" step="0.05" value={panX} onChange={(e) => setPanX(parseFloat(e.target.value))} className={`${range} block`} aria-label="Pan horizontally" />
                  </label>
                  <label>
                    Pan Y
                    <input type="range" min="-1" max="1" step="0.05" value={panY} onChange={(e) => setPanY(parseFloat(e.target.value))} className={`${range} block`} aria-label="Pan vertically" />
                  </label>
                </div>
              )}
            </ToolPanel>

            {/* signature whitening */}
            {preset.type === "signature" && (
              <ToolPanel>
                <div className="flex items-center justify-between gap-2">
                  <label className="flex items-center gap-1.5 text-[12px] font-bold text-ink">
                    <Sparkles className="size-3.5 text-saffron" /> Whiten paper background
                  </label>
                  <input type="checkbox" checked={cleanSignature} onChange={(e) => setCleanSignature(e.target.checked)} className="size-5 accent-saffron" aria-label="Whiten signature background" />
                </div>
                <p className="mt-1.5 text-[11px] leading-snug text-ink/60">
                  Removes yellow camera lighting &amp; shadows into crisp white scanner paper.
                </p>
              </ToolPanel>
            )}

            {/* photo name & date strip */}
            {preset.type === "photo" && (
              <ToolPanel>
                <div className="flex items-center justify-between gap-2">
                  <label className="text-[12px] font-bold text-ink">Add name &amp; date stamp</label>
                  <input type="checkbox" checked={addNameDate} onChange={(e) => setAddNameDate(e.target.checked)} className="size-5 accent-saffron" aria-label="Add name and date strip" />
                </div>
                {addNameDate && (
                  <div className="grid grid-cols-1 gap-2 pt-2 sm:grid-cols-2">
                    <input placeholder="Full name" className={smallInput} value={candidateName} onChange={(e) => setCandidateName(e.target.value)} aria-label="Candidate name" />
                    <input type="date" className={smallInput} value={photoDate} onChange={(e) => setPhotoDate(e.target.value)} aria-label="Date of photo" />
                  </div>
                )}
              </ToolPanel>
            )}
          </div>

          {/* preview + compliance */}
          {output && (
            <div className="flex flex-col items-center justify-between gap-4 rounded-lg border border-line bg-cream/30 p-4 sm:flex-row">
              <div className="flex flex-col items-center gap-3 sm:flex-row sm:gap-4">
                <div className="rounded-lg border border-line bg-white p-1.5">
                  <img src={output.url} alt="Compliance preview" className="max-h-28 rounded object-contain" />
                </div>
                <div className="space-y-1 text-center sm:text-left">
                  <div className="flex flex-wrap items-center justify-center gap-2 sm:justify-start">
                    <span className="text-[13px] font-bold text-ink">
                      {output.width}×{output.height} px
                    </span>
                    <Chip tone={isCompliant ? "green" : "saffron"}>
                      {isCompliant ? "Portal Ready" : "Size Out of Range"}
                    </Chip>
                  </div>
                  <p className="text-[12.5px] text-ink/60">
                    Output size:{" "}
                    <span className={`font-bold tabular-nums ${isCompliant ? "text-govgreen" : "text-alert"}`}>
                      {output.sizeKB} KB
                    </span>{" "}
                    <span className="text-[11px]">(target {minKB}–{maxKB} KB)</span>
                  </p>
                  <p className="text-[11px] text-ink/50">JPEG, no EXIF</p>
                </div>
              </div>

              <button
                onClick={download}
                disabled={processing}
                className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-saffron px-5 text-[14px] font-bold text-white transition-transform hover:-translate-y-0.5 disabled:opacity-60 sm:w-auto"
              >
                {processing ? <Loader2 className="size-4 animate-spin" /> : <Download className="size-4" />}
                Download Compliant JPEG
              </button>
            </div>
          )}
        </div>
      )}

      <canvas ref={canvasRef} className="hidden" aria-hidden="true" />

      <section className="mt-10 border-t border-line pt-8">
        <h2 className="text-[22px] font-extrabold tracking-tight text-ink">
          Photo and signature sizes by exam board
        </h2>
        <p className="mt-2 max-w-3xl text-[14.5px] leading-relaxed text-ink/70">
          These are the dimensions and file-size bands configured in the tool above. They are
          the limits most boards publish, but requirements change between exam cycles — confirm
          them in the notification PDF for your exam before you upload.
        </p>
        <div className="mt-5 overflow-x-auto">
          <table className="w-full border-collapse text-left text-[13.5px]">
            <thead>
              <tr className="border-b-2 border-ink font-bold">
                <th className="py-2 pr-4">Board</th>
                <th className="py-2 pr-4">Document</th>
                <th className="py-2 pr-4">Pixels</th>
                <th className="py-2 pr-4">File size</th>
                <th className="py-2">Official source</th>
              </tr>
            </thead>
            <tbody>
              {PRESETS.filter((preset) => preset.type !== "custom").map((preset) => (
                <tr key={preset.label} className="border-b border-line align-top">
                  <td className="py-2 pr-4 font-bold">{preset.board}</td>
                  <td className="py-2 pr-4">{preset.type === "photo" ? "Photo" : "Signature"}</td>
                  <td className="py-2 pr-4 tabular-nums">
                    {preset.width} × {preset.height}
                  </td>
                  <td className="py-2 pr-4 tabular-nums">
                    {preset.minKB}–{preset.maxKB} KB
                  </td>
                  <td className="py-2">
                    <a
                      href={preset.source}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-semibold underline underline-offset-2"
                    >
                      Board website
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mt-10">
        <h2 className="text-[22px] font-extrabold tracking-tight text-ink">Common questions</h2>
        <dl className="mt-4 space-y-5">
          {toolFaqs().map(({ question, answer }) => (
            <div key={question}>
              <dt className="text-[14.5px] font-bold text-ink">{question}</dt>
              <dd className="mt-1 max-w-3xl text-[14px] leading-relaxed text-ink/70">{answer}</dd>
            </div>
          ))}
        </dl>
      </section>
    </PageShell>
  );
}
