
// Default to Browser implementation for UI/Tauri
// Node users (scripts) should import from 'streaming.node' explicitly or we use a conditional export map
export * from './streaming.browser';
