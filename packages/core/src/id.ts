import { createHash, randomBytes } from "crypto";

/**
 * Generates a prefixed random ID.
 * e.g. generateId("mem")  → "mem_k7x2pq"
 *      generateId("edge") → "edge_a1b2c3"
 */
export function generateId(prefix: "mem" | "edge" | "ws" | "usr" | "apikey"): string {
  const suffix = randomBytes(4).toString("hex"); // 8 hex chars
  return `${prefix}_${suffix}`;
}

/**
 * Computes the SHA-256 content signature for a Memory Node.
 * Input is a deterministic JSON string of the content fields.
 */
export function computeSignature(fields: {
  title: object;
  content: object;
  tags: string[];
  author: string;
}): string {
  const payload = JSON.stringify({
    title: fields.title,
    content: fields.content,
    tags: [...fields.tags].sort(),
    author: fields.author,
  });
  return createHash("sha256").update(payload, "utf8").digest("hex");
}
