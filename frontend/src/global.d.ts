export {};

declare global {
  interface Window {
    openAIConfig?: () => void;
    triggerHITL?: (name: string, message: string, reason: string) => void;
  }
}
