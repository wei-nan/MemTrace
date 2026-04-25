import Ajv, { ErrorObject } from "ajv";
import addFormats from "ajv-formats";
import fs from "fs";
import path from "path";
import type { MemoryNode } from "./types";

const ajv = new Ajv();
addFormats(ajv);

let nodeValidator: any = null;
let edgeValidator: any = null;

function loadSchemas() {
  if (nodeValidator && edgeValidator) return;
  // This assumes packages/core is executed from workspace root or similar,
  // or we need to bundle the schemas. For now, reading relatively if exists,
  // otherwise throwing error to guide correct usage.
  
  const schemaDir = path.resolve(__dirname, "../../../schema");
  
  try {
    const nodeSchema = JSON.parse(fs.readFileSync(path.join(schemaDir, "node.v1.json"), "utf8"));
    const edgeSchema = JSON.parse(fs.readFileSync(path.join(schemaDir, "edge.v1.json"), "utf8"));
    
    nodeValidator = ajv.compile(nodeSchema);
    edgeValidator = ajv.compile(edgeSchema);
  } catch(e) {
    console.error("Failed to load JSON schemas from: " + schemaDir);
  }
}

export function validateNode(node: any): { valid: boolean; errors?: ErrorObject[] } {
  loadSchemas();
  if (!nodeValidator) return { valid: false };
  const valid = nodeValidator(node);
  return {
    valid,
    errors: nodeValidator.errors || undefined
  };
}

export function validateEdge(edge: any): { valid: boolean; errors?: ErrorObject[] } {
  loadSchemas();
  if (!edgeValidator) return { valid: false };
  const valid = edgeValidator(edge);
  return {
    valid,
    errors: edgeValidator.errors || undefined
  };
}

/**
 * Verifies the SHA-256 signature of a MemoryNode against its current content.
 * Uses the Web Crypto API (available in Node 18+ and browsers).
 * Returns true if the signature matches; false otherwise.
 */
export async function verifyNodeSignature(node: MemoryNode): Promise<boolean> {
  try {
    const content =
      (node.title["zh-TW"] ?? "") +
      (node.title.en ?? "") +
      (node.content.body["zh-TW"] ?? "") +
      (node.content.body.en ?? "");
    const encoder = new TextEncoder();
    const data = encoder.encode(content);
    const hashBuffer = await crypto.subtle.digest("SHA-256", data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    const hashHex = hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
    return hashHex === node.provenance.signature;
  } catch {
    return false;
  }
}
