// Ambient declarations for ONCE's text imports: package-once-red imports its
// bundled templates as text, and this compilation includes those sources.
declare module "*.tf" { const content: string; export default content; }
declare module "*.yml" { const content: string; export default content; }
declare module "*.yaml" { const content: string; export default content; }
declare module "*.cfg" { const content: string; export default content; }
declare module "*.ini" { const content: string; export default content; }
declare module "*/authorized-keys" { const content: string; export default content; }
declare module "*/deploy" { const content: string; export default content; }
declare module "*/once" { const content: string; export default content; }
