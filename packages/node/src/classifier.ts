// Classification order MUST match Python SDK: preference before correction
// This ensures "never use" → preference, not correction
const PATTERNS: [string, RegExp[]][] = [
  ["preference", [
    /(?:prefer|like|love|hate|favorite|best|worst)/i,
    /(?:always|never use|do not use)/i,
    /(?:use instead|switch to|my style|I want|keep it)/i,
  ]],
  ["correction", [
    /(?:actually|in fact|correction|wrong|not quite|instead)/i,
    /(?:should be|meant to|I meant)/i,
    /(?:don't|never|stop)/i,
  ]],
  ["temporal", [
    /(?:yesterday|today|tomorrow)/i,
    /(?:last|next)\s+(?:week|month|year)/i,
    /(?:ago|recently|deadline|reminder|schedule)/i,
    /(?:\d{4}[-/]\d{2}[-/]\d{2})/,
  ]],
  ["factual", [
    /(?:is|are|was|were|has|have|had)/i,
    /(?:located|found|based|lives)/i,
  ]],
];

export function classify(content: string): string {
  for (const [category, patterns] of PATTERNS) {
    for (const pattern of patterns) {
      if (pattern.test(content)) {
        return category;
      }
    }
  }
  return "general";
}
