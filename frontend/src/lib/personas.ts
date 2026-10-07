import { Briefcase, Cpu, Smile } from "lucide-react";
import type { ComponentType } from "react";
export type PersonaKey = "technical_hr" | "strict_manager" | "friendly_hr";
export interface PersonaStyle { label: string; tagline: string; topics: string[]; Icon: ComponentType<{ className?: string }>; solid: string; soft: string; text: string; border: string; hex: string }
export const PERSONAS: Record<PersonaKey, PersonaStyle> = {
  technical_hr: { label: "Technical HR", tagline: "Analytical and precise", topics: ["Technical knowledge", "Coding", "DSA", "Projects"], Icon: Cpu,
    solid: "bg-blue-600", soft: "bg-blue-50", text: "text-blue-700", border: "border-blue-200", hex: "#2563eb" },
  strict_manager: { label: "Strict Manager", tagline: "Direct and challenging", topics: ["Leadership", "Decision making", "Pressure handling", "Problem solving"], Icon: Briefcase,
    solid: "bg-rose-700", soft: "bg-rose-50", text: "text-rose-700", border: "border-rose-200", hex: "#be123c" },
  friendly_hr: { label: "Friendly HR", tagline: "Warm and conversational", topics: ["Communication", "Motivation", "Behavioral questions", "Career goals"], Icon: Smile,
    solid: "bg-emerald-600", soft: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-200", hex: "#059669" },
};
export const personaByLabel = (l: string) => Object.values(PERSONAS).find((p) => p.label === l) ?? PERSONAS.technical_hr;
export const personaByKey = (k: string) => PERSONAS[k as PersonaKey] ?? PERSONAS.technical_hr;
