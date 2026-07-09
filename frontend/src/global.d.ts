export {};

declare global {
  interface Window {
    triggerHITL?: (name: string, message: string, reason: string) => void;
  }
}

