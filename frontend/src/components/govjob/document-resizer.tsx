import { useEffect, useState } from "react";
import { Crop, Download, FileUp, Loader2 } from "lucide-react";
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

/**
 * Step 5: Government Photo & Signature Resizer.
 * Crops to the exact aspect ratio of the chosen exam preset, resizes to the
 * required pixel dimensions and compresses under the max KB limit — all
 * locally in the browser via canvas.
 */

interface ResizerPreset {
  label: string;
  width: number;
  height: number;
  maxKB: number;
}

const PRESETS: ResizerPreset[] = [
  { label: "SSC Photo (100×120, ≤50 KB)", width: 100, height: 120, maxKB: 50 },
  { label: "SSC Signature (140×60, ≤20 KB)", width: 140, height: 60, maxKB: 20 },
  { label: "IBPS Photo (200×230, ≤50 KB)", width: 200, height: 230, maxKB: 50 },
  { label: "IBPS Signature (140×60, ≤20 KB)", width: 140, height: 60, maxKB: 20 },
  { label: "UPSC Photo (350×350, ≤300 KB)", width: 350, height: 350, maxKB: 300 },
  { label: "UPSC Signature (350×150, ≤300 KB)", width: 350, height: 150, maxKB: 300 },
  { label: "Custom (max 50 KB)", width: 0, height: 0, maxKB: 50 },
];

interface OutputImage {
  url: string;
  sizeKB: number;
  width: number;
  height: number;
}

export function DocumentResizer() {
  const [presetIdx, setPresetIdx] = useState(0);
  const [customWidth, setCustomWidth] = useState("200");
  const [customHeight, setCustomHeight] = useState("230");
  const [srcUrl, setSrcUrl] = useState<string | null>(null);
  const [srcInfo, setSrcInfo] = useState<{
    name: string;
    width: number;
    height: number;
    sizeKB: number;
  } | null>(null);
  const [output, setOutput] = useState<OutputImage | null>(null);
  const [processing, setProcessing] = useState(false);

  const preset = PRESETS[presetIdx]!;
  const targetWidth = preset.width || Math.max(1, parseInt(customWidth, 10) || 0);
  const targetHeight = preset.height || Math.max(1, parseInt(customHeight, 10) || 0);

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

      // Cover-crop: fill the target box while preserving aspect ratio.
      const srcAspect = img.width / img.height;
      const dstAspect = targetWidth / targetHeight;
      let cropW = img.width;
      let cropH = img.height;
      if (srcAspect > dstAspect) {
        cropW = img.height * dstAspect;
      } else {
        cropH = img.width / dstAspect;
      }
      const cropX = (img.width - cropW) / 2;
      const cropY = (img.height - cropH) / 2;

      const canvas = document.createElement("canvas");
      canvas.width = targetWidth;
      canvas.height = targetHeight;
      const ctx = canvas.getContext("2d");
      if (!ctx) throw new Error("Canvas unavailable");
      ctx.imageSmoothingQuality = "high";
      ctx.drawImage(img, cropX, cropY, cropW, cropH, 0, 0, targetWidth, targetHeight);

      // Compress downward until under the preset's KB limit.
      let quality = 0.92;
      let blob = await new Promise<Blob>((resolve) =>
        canvas.toBlob((b) => resolve(b as Blob), "image/jpeg", quality),
      );
      while (blob.size > preset.maxKB * 1024 && quality > 0.15) {
        quality -= 0.07;
        blob = await new Promise<Blob>((resolve) =>
          canvas.toBlob((b) => resolve(b as Blob), "image/jpeg", quality),
        );
      }

      setOutput({
        url: URL.createObjectURL(blob),
        sizeKB: Math.round(blob.size / 102.4) / 10,
        width: targetWidth,
        height: targetHeight,
      });
    } finally {
      setProcessing(false);
    }
  };

  useEffect(() => {
    if (srcUrl) void process();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [presetIdx, customWidth, customHeight, srcUrl]);

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const url = URL.createObjectURL(file);
    setSrcUrl(url);
    setOutput(null);
    const probe = new Image();
    probe.onload = () =>
      setSrcInfo({
        name: file.name,
        width: probe.width,
        height: probe.height,
        sizeKB: Math.round(file.size / 102.4) / 10,
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
              Crop, resize and compress to each exam board's exact pixel and file-size limits —
              processed entirely in your browser.
            </CardDescription>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-5">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
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
          {preset.width === 0 && (
            <>
              <div className="space-y-1.5">
                <Label className="text-xs text-muted-foreground">Width (px)</Label>
                <Input
                  type="number"
                  min={1}
                  value={customWidth}
                  onChange={(e) => setCustomWidth(e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-muted-foreground">Height (px)</Label>
                <Input
                  type="number"
                  min={1}
                  value={customHeight}
                  onChange={(e) => setCustomHeight(e.target.value)}
                />
              </div>
            </>
          )}
          {preset.width !== 0 && (
            <div className="space-y-1.5 md:col-span-2">
              <Label className="text-xs text-muted-foreground">Requirements</Label>
              <div className="flex h-10 items-center gap-2">
                <Badge variant="secondary">
                  {preset.width} × {preset.height} px
                </Badge>
                <Badge variant="outline">≤ {preset.maxKB} KB · JPEG</Badge>
              </div>
            </div>
          )}
        </div>

        <label
          className={cn(
            "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border border-dashed bg-muted/30 px-6 py-10 text-center transition hover:border-primary/50 hover:bg-muted/50",
            processing && "pointer-events-none opacity-70",
          )}
        >
          {processing ? (
            <Loader2 className="size-6 animate-spin text-primary" />
          ) : (
            <FileUp className="size-6 text-muted-foreground" />
          )}
          <span className="text-sm font-medium">
            {srcInfo ? srcInfo.name : "Click to select a photo or signature image"}
          </span>
          {srcInfo && (
            <span className="text-xs text-muted-foreground">
              Original: {srcInfo.width} × {srcInfo.height} px · {srcInfo.sizeKB} KB
            </span>
          )}
          <input type="file" accept="image/*" className="hidden" onChange={handleFile} />
        </label>

        {output && (
          <div className="flex flex-col items-start gap-4 rounded-xl border bg-muted/30 p-4 sm:flex-row sm:items-center sm:justify-between">
            <img
              src={output.url}
              alt="Resized output preview"
              className="max-h-32 rounded-lg border bg-background object-contain"
            />
            <div className="text-xs text-muted-foreground">
              <p>
                Output:{" "}
                <span className="font-medium text-foreground">
                  {output.width} × {output.height} px
                </span>
              </p>
              <p>
                File size:{" "}
                <span
                  className={cn(
                    "font-medium",
                    output.sizeKB <= preset.maxKB ? "text-success" : "text-destructive",
                  )}
                >
                  {output.sizeKB} KB
                </span>{" "}
                (limit {preset.maxKB} KB)
              </p>
            </div>
            <Button onClick={download} className="gap-2 rounded-xl">
              <Download className="size-4" />
              Download JPEG
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
