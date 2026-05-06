import type { AppData, GroupData } from "./model";

const STORAGE_KEY = "calotrack:data:v1";

const nowIso = () => new Date().toISOString();

export function loadAppData(): AppData {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { version: 1, groups: {} };
    const parsed = JSON.parse(raw) as AppData;
    if (!parsed || parsed.version !== 1 || typeof parsed.groups !== "object") {
      return { version: 1, groups: {} };
    }
    return parsed;
  } catch {
    return { version: 1, groups: {} };
  }
}

export function saveAppData(data: AppData): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
}

export function upsertGroup(group: GroupData): void {
  const data = loadAppData();
  data.groups[group.groupId] = { ...group, updatedAt: nowIso(), version: 1 };
  saveAppData(data);
}

export function getGroup(groupId: string): GroupData | undefined {
  const data = loadAppData();
  return data.groups[groupId];
}

export function deleteGroup(groupId: string): void {
  const data = loadAppData();
  delete data.groups[groupId];
  saveAppData(data);
}

export function exportAllData(): string {
  return JSON.stringify(loadAppData(), null, 2);
}

export function importAllData(jsonText: string): void {
  const parsed = JSON.parse(jsonText) as AppData;
  if (!parsed || parsed.version !== 1 || typeof parsed.groups !== "object") {
    throw new Error("JSON invalide (version/modèle)");
  }
  saveAppData(parsed);
}

