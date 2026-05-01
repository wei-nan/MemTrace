/**
 * Document segmentation utilities for Phase 4.2
 */

export interface Segment {
  id: string;
  heading: string;
  headingChain: string[];
  content: string;
  startIndex: number;
  endIndex: number;
}

/**
 * Splits a Markdown document into segments based on headings.
 * Respects code blocks and tables (won't split inside them).
 * 
 * @param text The raw markdown text
 * @param maxChunkSize Maximum size of a segment (if a section is too long, it's split by paragraphs)
 */
export function segmentDocument(text: string, maxChunkSize: number = 4000): Segment[] {
  const segments: Segment[] = [];
  
  // 1. Identify all heading boundaries
  // Regex to find Markdown headings (at start of line)
  const headingRegex = /^(#{1,6})\s+(.+)$/gm;
  
  // 2. Identify code block boundaries to avoid splitting inside them
  const codeBlockRegex = /^```[\s\S]*?^```/gm;
  const codeBlocks: [number, number][] = [];
  let match;
  while ((match = codeBlockRegex.exec(text)) !== null) {
    codeBlocks.push([match.index, match.index + match[0].length]);
  }

  // Helper to check if a position is inside a code block
  const isInsideCodeBlock = (pos: number) => {
    return codeBlocks.some(([start, end]) => pos >= start && pos < end);
  };

  const headings: { level: number; title: string; index: number }[] = [];
  while ((match = headingRegex.exec(text)) !== null) {
    if (!isInsideCodeBlock(match.index)) {
      headings.push({
        level: match[1].length,
        title: match[2].trim(),
        index: match.index
      });
    }
  }

  // 3. Create segments based on headings
  if (headings.length === 0) {
    // No headings found, split by size
    return splitByParagraphs(text, [], maxChunkSize, 0);
  }

  // Current heading chain (ancestors)
  let currentChain: { level: number; title: string }[] = [];

  for (let i = 0; i < headings.length; i++) {
    const h = headings[i];
    const nextH = headings[i + 1];
    const start = h.index;
    const end = nextH ? nextH.index : text.length;
    
    // Update chain
    currentChain = currentChain.filter(item => item.level < h.level);
    currentChain.push({ level: h.level, title: h.title });
    
    const headingChainStrings = currentChain.map(c => c.title);
    const content = text.substring(start, end).trim();
    
    if (content.length > maxChunkSize) {
      // Too large, split further by paragraphs while keeping the chain
      segments.push(...splitByParagraphs(content, headingChainStrings, maxChunkSize, start));
    } else {
      segments.push({
        id: `seg_${start}`,
        heading: h.title,
        headingChain: headingChainStrings,
        content,
        startIndex: start,
        endIndex: end
      });
    }
  }

  return segments;
}

/**
 * Splits a chunk of text by paragraphs if it exceeds maxChunkSize.
 */
function splitByParagraphs(text: string, headingChain: string[], maxSize: number, offset: number): Segment[] {
  if (text.length <= maxSize) {
    return [{
      id: `seg_p_${offset}`,
      heading: headingChain[headingChain.length - 1] || 'General',
      headingChain,
      content: text,
      startIndex: offset,
      endIndex: offset + text.length
    }];
  }

  const chunks: Segment[] = [];
  let currentStart = 0;
  
  while (currentStart < text.length) {
    let currentEnd = Math.min(currentStart + maxSize, text.length);
    
    if (currentEnd < text.length) {
      // Try to find the last paragraph break
      const lastPara = text.lastIndexOf('\n\n', currentEnd);
      if (lastPara > currentStart + (maxSize / 3)) {
        currentEnd = lastPara;
      } else {
        // Try single newline
        const lastLine = text.lastIndexOf('\n', currentEnd);
        if (lastLine > currentStart + (maxSize / 2)) {
          currentEnd = lastLine;
        }
      }
    }
    
    const content = text.substring(currentStart, currentEnd).trim();
    if (content) {
      chunks.push({
        id: `seg_p_${offset + currentStart}`,
        heading: headingChain[headingChain.length - 1] || 'General',
        headingChain,
        content,
        startIndex: offset + currentStart,
        endIndex: offset + currentEnd
      });
    }
    
    currentStart = currentEnd;
  }
  
  return chunks;
}

/**
 * Injects the heading chain context into the segment content.
 * e.g., "[§Section] > [§SubSection] > Content..."
 */
export function injectContext(segment: Segment): string {
  if (segment.headingChain.length === 0) return segment.content;
  
  const chainPrefix = segment.headingChain
    .map(title => `[§${title}]`)
    .join(' > ');
    
  return `${chainPrefix}\n\n${segment.content}`;
}
