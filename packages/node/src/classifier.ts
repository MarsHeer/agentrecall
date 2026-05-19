const PATTERNS: Record<string, RegExp[]> = {
  correction: [
    /(?:actually|in fact|correction|wrong|not quite|instead)/i,
    /(?:should be|meant to|I meant)/i,
  ],
  preference: [
    /(?:prefer|like|love|hate|favorite|best|worst)/i,
    /(?:always|never|don't|do not)/i,
    /(?:use|use instead|switch to)/i,
  ],
  temporal: [
    /(?:yesterday|today|tomorrow|last (?:week|month|year))/i,
    /(?:next (?:week|month|year)|ago|recently)/i,
    /(?:\d{4}[-/]\d{2}[-/]\d{2})/,
  ],
  factual: [
    /(?:is|are|was|were|has|have|had)/i,
    /(?:located|found|based|sits|lives)/i,
  ],
};

export function classify(content: string): string {
  for (const [category, patterns] of Object.entries(PATTERNS)) {
    for (const pattern of patterns) {
      if (pattern.test(content)) {
        return category;
      }
    }
  }
  return "general";
}
