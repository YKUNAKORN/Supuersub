# Hand-off contract between the supersub skills

<!-- Synchronised copy. The master lives in the plugin repository's shared folder and
     is copied into each skill that needs it. Edit the master, never this copy. -->

Five skills in the `supersub` plugin form a pipeline. Each one must also work alone.

```
design-md ──▶ mock-ui ──▶ create-app
                 │
                 ├──▶ create-list   (data the screens need)
                 └──▶ create-flow   (actions the screens trigger)
```

## Where each artifact goes

Artifacts have fixed names so a later skill can find what an earlier one produced.
When a project folder is writable, write them there:

```
<project>/
├── DESIGN.md                      design-md   (project root, where other tools expect it)
└── supersub/
    ├── mockup/                    mock-ui
    │   ├── index.html             screen map that links to every screen
    │   ├── <screen-file>.html     one file per screen
    │   └── sitemap.json           screens, navigation edges, data and action hints
    ├── app/                       create-app
    │   ├── <ScreenId>.pa.yaml
    │   └── PASTE-ORDER.md
    ├── lists/                     create-list
    │   ├── lists.md               schema overview the user approves
    │   ├── <ListName>.list.json   machine-readable spec, one per list
    │   └── <ListName>.xlsx | .csv import file
    └── flows/                     create-flow
        ├── flow.md                flow inventory the user approves
        ├── <FlowName>.flow.json   machine-readable spec, one per flow
        └── <FlowName>_LegacyPackage.zip
```

When there is no project folder (a chat conversation), create the files with exactly
these names and hand them to the user as downloads. They come back later as attachments.

## Rules

1. **Never assume the previous skill ran.** Accept the upstream artifact as a path, an
   attachment or pasted text. If something you need is missing, say what is missing and
   ask for it. Do not invent it.
2. **Identifiers are ASCII.** Screen ids are `scr` + PascalCase (`scrHome`). List and
   column internal names are PascalCase with no spaces. Token names in `DESIGN.md` are
   lowercase kebab-case (`button-primary`, `on-surface`). Display text may be in any
   language.
3. **Name the next skill.** Every skill ends its hand-off by naming the skill that can use
   its output next.
4. **Reply in the user's language.** User-facing text inside generated artifacts (labels,
   display names, notes, prose) follows the user's language. Identifiers stay ASCII.

## Targets

A design is made for one of two targets:

- `web`: the default when `design-md` or `mock-ui` is used on its own.
- `power-apps`: the result is headed for `create-app`. Design and markup stay inside what
  the `create-app` catalog can reproduce. The Power Apps profile, when a skill ships one,
  lists exactly what that is. The default canvas is 1366 × 768, a convention inherited
  from `create-app`, not a sourced Power Apps default.

State the target at the top of every artifact that depends on it, so a later skill does
not have to guess.
