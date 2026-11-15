import { useEffect, useRef, useState } from "react";
import { Crop, Download, FileUp, Loader2, RefreshCw, Sparkles, ZoomIn } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

interface ResizerPreset {
  label: string;
  width: number;
  height: number;
  minKB: number;
  maxKB: number;
  type: "photo" | "signature" | "custom";
}

const PRESETS: ResizerPreset[] = [
  {
    label: "SSC Photo (350×450, 20–50 KB)",
    width: 350,
    height: 450,
    minKB: 20,
    maxKB: 50,
    type: "photo",
  },
  {
    label: "SSC Signature (280×120, 10–20 KB)",
    width: 280,
    height: 120,
    minKB: 10,
    maxKB: 20,
    type: "signature",
  },
  {
    label: "IBPS Photo (200×230, 20–50 KB)",
    width: 200,
    height: 230,
    minKB: 20,
    maxKB: 50,
    type: "photo",
  },
  {
    label: "IBPS Signature (140×60, 10–20 KB)",
    width: 140,
    height: 60,
    minKB: 10,
    maxKB: 20,
    type: "signature",
  },
  {
    label: "UPSC Photo (350×350, 20–300 KB)",
    width: 350,
    height: 350,
    minKB: 20,
    maxKB: 300,
    type: "photo",
  },
  {
    label: "UPSC Signature (350×150, 20–300 KB)",
    width: 350,
    height: 150,
    minKB: 20,
    maxKB: 300,
    type: "signature",
  },
  {
    label: "Custom (Self Defined)",
    width: 0,
    height: 0,
    minKB: 10,
    maxKB: 50,
    type: "custom",
  },
];

interface OutputImage {
  url: string;
  sizeKB: number;
  width: number;
  height: number;
  blob: Blob;
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

  // Processing & adjustment states
  const [zoom, setZoom] = useState(1);
  const [panX, setPanX] = useState(0);
  const [panY, setPanY] = useState(0);
  const [cleanSignature, setCleanSignature] = useState(true);
  const [addNameDate, setAddNameDate] = useState(false);
  const [candidateName, setCandidateName] = useState("");
  const [photoDate, setPhotoDate] = useState(new Date().toISOString().split("T")[0]);

  const [output, setOutput] = useState<OutputImage | null>(null);
  const [processing, setProcessing] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const preset = PRESETS[presetIdx]!;
  const targetWidth = preset.width || Math.max(1, parseInt(customWidth, 10) || 300);
  const targetHeight = preset.height || Math.max(1, parseInt(customHeight, 10) || 300);
  const maxKB = preset.type === "custom" ? parseInt(customMaxKB, 10) || 50 : preset.maxKB;
  const minKB = preset.minKB;

  // Binary search image compression engine
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

    // Safety fallback: slightly downscale if quality reduction alone exceeded bounds
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
      const ctx = canvas.getContext("2d");
      if (!ctx) throw new Error("Canvas unavailable");

      // White solid base background
      ctx.fillStyle = "#FFFFFF";
      ctx.fillRect(0, 0, targetWidth, targetHeight);
      ctx.imageSmoothingEnabled = true;
      ctx.imageSmoothingQuality = "high";

      // Cover-crop calculation with Zoom and Pan offsets
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

      const cropX = Math.max(
        0,
        Math.min(img.width - drawW, (img.width - drawW) / 2 + panX * maxPanX),
      );
      const cropY = Math.max(
        0,
        Math.min(img.height - drawH, (img.height - drawH) / 2 + panY * maxPanY),
      );

      ctx.drawImage(img, cropX, cropY, drawW, drawH, 0, 0, targetWidth, targetHeight);

      // Adaptive Binarization for Signatures (cleans yellow/gray paper into #FFFFFF and sharpens ink)
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

      // Candidate Name & Date of Photo (DOP) Strip
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

      // Run binary-search compression
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
    <Card>
      <CardHeader className="pb-5">
        <div className="flex items-start gap-3">
          <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <Crop className="size-5" />
          </span>
          <div>
            <CardTitle className="text-lg">Government Photo &amp; Signature Resizer</CardTitle>
            <CardDescription className="mt-1">
              Crop, resize, clean, and compress to each exam board's exact pixel and file-size
              limits — processed entirely in your browser.
            </CardDescription>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-5">
        {/* Preset Selection & Dimensions Row */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">Exam Board Preset</Label>
            <Select value={String(presetIdx)} onValueChange={(v) => setPresetIdx(Number(v))}>
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PRESETS.map((p, i) => (
                  <SelectItem key={p.label} value={String(i)}>
                    {p.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {preset.type === "custom" ? (
            <>
              <div className="space-y-1.5">
                <Label className="text-xs text-muted-foreground">Width × Height (px)</Label>
                <div className="flex gap-2">
                  <Input
                    type="number"
                    min={1}
                    value={customWidth}
                    placeholder="W"
                    onChange={(e) => setCustomWidth(e.target.value)}
                  />
                  <Input
                    type="number"
                    min={1}
                    value={customHeight}
                    placeholder="H"
                    onChange={(e) => setCustomHeight(e.target.value)}
                  />
                </div>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-muted-foreground">Max File Size (KB)</Label>
                <Input
                  type="number"
                  min={5}
                  value={customMaxKB}
                  onChange={(e) => setCustomMaxKB(e.target.value)}
                />
              </div>
            </>
          ) : (
            <div className="space-y-1.5 lg:col-span-2">
              <Label className="text-xs text-muted-foreground">Statutory Requirements</Label>
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="secondary">
                  {preset.width} × {preset.height} px
                </Badge>
                <Badge variant="outline">
                  {preset.minKB} KB – {preset.maxKB} KB · JPEG
                </Badge>
                <Badge variant={preset.type === "photo" ? "default" : "secondary"}>
                  {preset.type === "photo" ? "Passport Photo" : "Signature"}
                </Badge>
              </div>
            </div>
          )}
        </div>

        {/* Upload Dropzone */}
        {!srcUrl && (
          <label
            className={cn(
              "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border border-dashed bg-muted/30 px-6 py-12 text-center transition hover:border-primary/50 hover:bg-muted/50",
              processing && "pointer-events-none opacity-70",
            )}
          >
            {processing ? (
              <Loader2 className="size-8 animate-spin text-primary" />
            ) : (
              <FileUp className="size-8 text-muted-foreground" />
            )}
            <span className="text-sm font-medium">Click to select a photo or signature image</span>
            <span className="text-xs text-muted-foreground">
              Supports JPG, PNG, WEBP — Auto converts to portal-compliant JPEG
            </span>
            <input type="file" accept="image/*" className="hidden" onChange={handleFile} />
          </label>
        )}

        {/* Live Workspace when image is loaded */}
        {srcUrl && (
          <div className="space-y-4 rounded-xl border bg-muted/20 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b pb-3">
              <div className="flex min-w-0 items-center gap-2">
                <span className="max-w-[200px] truncate text-xs font-semibold sm:max-w-none">
                  {srcInfo?.name}
                </span>
                {srcInfo && (
                  <span className="text-xs text-muted-foreground">
                    ({srcInfo.width}×{srcInfo.height} px · {srcInfo.sizeKB} KB)
                  </span>
                )}
              </div>
              <label className="shrink-0 cursor-pointer text-xs font-medium text-primary hover:underline">
                Replace File
                <input type="file" accept="image/*" className="hidden" onChange={handleFile} />
              </label>
            </div>

            {/* Adjustments & Fine Tuning Toolbar */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {/* Zoom & Positioning */}
              <div className="space-y-2 rounded-lg border bg-background/60 p-3">
                <div className="flex items-center justify-between">
                  <Label className="flex items-center gap-1.5 text-xs font-medium">
                    <ZoomIn className="size-3.5 text-primary" /> Zoom ({zoom.toFixed(1)}x)
                  </Label>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 px-1.5 text-xs"
                    onClick={() => {
                      setZoom(1);
                      setPanX(0);
                      setPanY(0);
                    }}
                  >
                    <RefreshCw className="size-3 mr-1" /> Reset
                  </Button>
                </div>
                <input
                  type="range"
                  min="1"
                  max="2.5"
                  step="0.05"
                  value={zoom}
                  onChange={(e) => setZoom(parseFloat(e.target.value))}
                  className="w-full accent-primary cursor-pointer"
                />
                {zoom > 1 && (
                  <div className="grid grid-cols-2 gap-2 pt-1 text-[11px] text-muted-foreground">
                    <label>
                      Pan X
                      <input
                        type="range"
                        min="-1"
                        max="1"
                        step="0.05"
                        value={panX}
                        onChange={(e) => setPanX(parseFloat(e.target.value))}
                        className="w-full accent-primary"
                      />
                    </label>
                    <label>
                      Pan Y
                      <input
                        type="range"
                        min="-1"
                        max="1"
                        step="0.05"
                        value={panY}
                        onChange={(e) => setPanY(parseFloat(e.target.value))}
                        className="w-full accent-primary"
                      />
                    </label>
                  </div>
                )}
              </div>

              {/* Signature Background Whitening */}
              {preset.type === "signature" && (
                <div className="space-y-2 rounded-lg border bg-background/60 p-3">
                  <div className="flex items-center justify-between">
                    <Label className="flex items-center gap-1.5 text-xs font-medium">
                      <Sparkles className="size-3.5 text-primary" /> Whiten Paper Background
                    </Label>
                    <input
                      type="checkbox"
                      checked={cleanSignature}
                      onChange={(e) => setCleanSignature(e.target.checked)}
                      className="size-4 rounded accent-primary cursor-pointer"
                    />
                  </div>
                  <p className="text-[11px] text-muted-foreground leading-relaxed">
                    Automatically removes yellow camera lighting & shadows into crisp #FFFFFF
                    scanner white.
                  </p>
                </div>
              )}

              {/* Photo Name & Date Stamp */}
              {preset.type === "photo" && (
                <div className="space-y-2 rounded-lg border bg-background/60 p-3 sm:col-span-2 lg:col-span-2">
                  <div className="flex items-center justify-between">
                    <Label className="text-xs font-medium">
                      Add Candidate Name &amp; Date Stamp
                    </Label>
                    <input
                      type="checkbox"
                      checked={addNameDate}
                      onChange={(e) => setAddNameDate(e.target.checked)}
                      className="size-4 rounded accent-primary cursor-pointer"
                    />
                  </div>
                  {addNameDate && (
                    <div className="grid grid-cols-1 gap-2 pt-1 sm:grid-cols-2">
                      <Input
                        placeholder="Full Candidate Name"
                        className="h-8 text-xs"
                        value={candidateName}
                        onChange={(e) => setCandidateName(e.target.value)}
                      />
                      <Input
                        type="date"
                        className="h-8 text-xs"
                        value={photoDate}
                        onChange={(e) => setPhotoDate(e.target.value)}
                      />
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Preview & Compliance Status Bar */}
            {output && (
              <div className="flex flex-col items-center justify-between gap-4 rounded-xl border bg-background p-4 sm:flex-row">
                <div className="flex flex-col items-center gap-3 sm:flex-row sm:gap-4">
                  <div className="relative flex items-center justify-center rounded-lg border bg-muted/20 p-1.5">
                    <img
                      src={output.url}
                      alt="Compliance preview"
                      className="max-h-28 rounded object-contain shadow-sm"
                    />
                  </div>

                  <div className="space-y-1 text-center text-xs sm:text-left">
                    <div className="flex flex-wrap items-center justify-center gap-2 sm:justify-start">
                      <span className="font-semibold text-foreground">
                        {output.width} × {output.height} px
                      </span>
                      <Badge
                        variant={isCompliant ? "default" : "destructive"}
                        className="text-[10px] h-5"
                      >
                        {isCompliant ? "Portal Ready" : "Size Out of Range"}
                      </Badge>
                    </div>

                    <p className="text-muted-foreground">
                      Output Size:{" "}
                      <span
                        className={cn(
                          "font-bold",
                          isCompliant ? "text-emerald-500" : "text-destructive",
                        )}
                      >
                        {output.sizeKB} KB
                      </span>{" "}
                      <span className="text-[11px]">
                        (Target: {minKB}–{maxKB} KB)
                      </span>
                    </p>
                    <p className="text-[11px] text-muted-foreground">
                      Format: Pure JPEG (Standard EXIF)
                    </p>
                  </div>
                </div>

                <Button
                  onClick={download}
                  className="gap-2 rounded-xl w-full sm:w-auto"
                  disabled={processing}
                >
                  {processing ? (
                    <Loader2 className="size-4 animate-spin" />
                  ) : (
                    <Download className="size-4" />
                  )}
                  Download Compliant JPEG
                </Button>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
