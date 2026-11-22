export interface ResizerPreset {
  label: string;
  width: number;
  height: number;
  minKB: number;
  maxKB: number;
  type: "photo" | "signature" | "custom";
  board: string;
  source: string;
}

/**
 * Dimensions configured in the resizer. These are the limits most commonly
 * published by each board; always confirm against the specific notification
 * PDF, because requirements change between cycles.
 */
export const PRESETS: ResizerPreset[] = [
  { label: "SSC Photo (350×450, 20–50 KB)", width: 350, height: 450, minKB: 20, maxKB: 50, type: "photo", board: "SSC", source: "https://ssc.gov.in/" },
  { label: "SSC Signature (280×120, 10–20 KB)", width: 280, height: 120, minKB: 10, maxKB: 20, type: "signature", board: "SSC", source: "https://ssc.gov.in/" },
  { label: "IBPS Photo (200×230, 20–50 KB)", width: 200, height: 230, minKB: 20, maxKB: 50, type: "photo", board: "IBPS", source: "https://www.ibps.in/" },
  { label: "IBPS Signature (140×60, 10–20 KB)", width: 140, height: 60, minKB: 10, maxKB: 20, type: "signature", board: "IBPS", source: "https://www.ibps.in/" },
  { label: "UPSC Photo (350×350, 20–300 KB)", width: 350, height: 350, minKB: 20, maxKB: 300, type: "photo", board: "UPSC", source: "https://upsc.gov.in/" },
  { label: "UPSC Signature (350×150, 20–300 KB)", width: 350, height: 150, minKB: 20, maxKB: 300, type: "signature", board: "UPSC", source: "https://upsc.gov.in/" },
  { label: "Custom (Self Defined)", width: 0, height: 0, minKB: 10, maxKB: 50, type: "custom", board: "Other", source: "https://www.rozgarboard.in/methodology" },
];

export function toolFaqs(): Array<{ question: string; answer: string }> {
  return [
    {
      question: "Does the tool upload my photo anywhere?",
      answer: "No. Resizing, cropping and compression all happen in your browser with the Canvas API. Your image is never sent to a server, so nothing is stored or logged.",
    },
    {
      question: "What size should an SSC photo be?",
      answer: "This tool is configured for 350 × 450 pixels at 20–50 KB. Confirm the exact limits in the notification PDF for your exam cycle before uploading.",
    },
    {
      question: "Why was my government exam photo rejected?",
      answer: "The usual causes are a white or dark background, a file outside the stated KB range, wrong pixel dimensions, or a blurred face. The tool checks size and dimensions; check the background and framing yourself.",
    },
    {
      question: "Can I use a JPEG from my phone?",
      answer: "Yes. The tool outputs a JPEG, which is what most government portals accept. If your notification asks for a different format, do not use this tool for that application.",
    },
    {
      question: "Does the signature need my name and date?",
      answer: "Many boards ask you to sign on white paper with your name and date below the signature. The tool can add that text for signatures; check your notification for the exact wording.",
    },
  ];
}
