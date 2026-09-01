// rule-and-excel-toolkit-dsh: the "rule-and-excel-toolkit" skill as a DSH bundle.
//
// A Cordis plugin that registers one skill provider into the HOST layer of the
// `ctx.skills` registry, so every agent preset's scope chain sees this skill.
// The skill body lives at `../skills/rule-and-excel-toolkit/SKILL.md` inside this
// package, with its `scripts/` directory beside it. The provider locates them
// from `import.meta.url` (an assembly fact of this package, never user config),
// and exposes the skill directory as the resource base so the body's relative
// `scripts/xxx.py` references resolve when the skill is loaded.
//
// The provider protocol mirrors @deepseek-ai/dsh-skill-filesystem:
//   - list()  returns the single directory-bundle candidate (name/description
//     from YAML frontmatter; the body stays unread until requested)
//   - get()   parses the SKILL.md and returns the full definition with a
//     directory resource base
import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const name = 'rule-and-excel-toolkit-dsh'
const inject = ['skills']

/** Registry precedence for packaged skill providers: ranks below the local
 * bundled root so a project- or user-local copy of the same skill wins over
 * this packaged one. */
const PACKAGED_SKILL_RANK = 550

/** The source bucket this skill advertises under (prompt-visible metadata). */
const SOURCE = 'custom'

/** The single skill this bundle ships. */
const SKILL_NAME = 'rule-and-excel-toolkit'

/**
 * Parse the YAML frontmatter block of a SKILL.md into metadata plus body.
 * Handles the scalar fields DSH skill discovery consumes (name, description,
 * whenToUse) plus invocation flags, and supports folded scalar blocks
 * (`description: >` followed by indented lines) — folded lines are joined with
 * single spaces, matching YAML semantics. Richer metadata passes through verbatim.
 * @param text - the raw skill file contents.
 * @returns parsed metadata object and the markdown body after the block, or
 *   null when the file has no frontmatter block at all.
 */
function parseFrontmatter(text) {
  if (!text.startsWith('---')) return null
  const end = text.indexOf('\n---', 3)
  if (end === -1) return null
  const block = text.slice(3, end)
  const body = text.slice(end + 4).replace(/^\n+/, '')
  const metadata = {}
  let currentKey = null
  let folded = false
  for (const rawLine of block.split('\n')) {
    const line = rawLine.trimEnd()
    if (/^[ \t]/.test(line) && currentKey !== null) {
      const value = line.trim()
      if (value) {
        metadata[currentKey] = folded
          ? `${metadata[currentKey]} ${value}`
          : `${metadata[currentKey]}\n${value}`
      }
      continue
    }
    const match = /^([A-Za-z][\w-]*):\s*(.*)$/.exec(line)
    if (!match) {
      currentKey = null
      folded = false
      continue
    }
    let value = match[2].trim()
    folded = value === '>' || value === '>-' || value === '>+'
    if (folded) {
      value = ''
    } else if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1)
    }
    metadata[match[1]] = value
    currentKey = folded ? match[1] : null
  }
  return { metadata, body }
}

/**
 * Read and parse the skill's SKILL.md.
 * @param skillFile - absolute path to the SKILL.md file.
 * @param signal - optional cancellation; aborts the read.
 * @returns the parsed skill record, or undefined when the file vanished.
 */
async function parseSkillFile(skillFile, signal) {
  let text
  try {
    text = await readFile(skillFile, 'utf8')
  } catch {
    return undefined
  }
  if (signal?.aborted) return undefined
  const parsed = parseFrontmatter(text)
  if (parsed === null) return undefined
  return {
    name: parsed.metadata.name ?? '',
    description: parsed.metadata.description ?? '',
    whenToUse: parsed.metadata.whenToUse,
    metadata: parsed.metadata,
    content: parsed.body,
  }
}

/**
 * Map frontmatter invocation flags onto DSH's invocation record. Omitted flags
 * keep the skill both model- and user-invocable; `disable-model-invocation:
 * true` makes it user-only.
 * @param metadata - parsed frontmatter metadata.
 * @returns the DSH invocation record.
 */
function invocationFrom(metadata) {
  if (metadata['disable-model-invocation'] === 'true' || metadata['disable-model-invocation'] === true) {
    return { modelInvocable: false, userInvocable: true }
  }
  if (metadata['user-invocable'] === 'false' || metadata['user-invocable'] === false) {
    return { modelInvocable: true, userInvocable: false }
  }
  return { modelInvocable: true, userInvocable: true }
}

/** Register the packaged skill provider on `ctx.skills`. */
function apply(ctx) {
  const skillDir = join(dirname(fileURLToPath(import.meta.url)), '..', 'skills', SKILL_NAME)
  const skillFile = join(skillDir, 'SKILL.md')
  ctx.skills.registerProvider(() => ({
    name,
    async list(options) {
      const parsed = await parseSkillFile(skillFile, options?.signal)
      if (parsed === undefined) return []
      return [{
        name: parsed.name,
        description: parsed.description,
        ...(parsed.whenToUse !== undefined ? { whenToUse: parsed.whenToUse } : {}),
        invocation: invocationFrom(parsed.metadata),
        source: SOURCE,
        provider: name,
        rank: PACKAGED_SKILL_RANK,
        locator: skillDir,
        path: skillFile,
        ...(Object.keys(parsed.metadata).length > 0 ? { metadata: parsed.metadata } : {}),
      }]
    },
    async get(candidate, options) {
      const parsed = await parseSkillFile(candidate.path, options?.signal)
      if (parsed === undefined) return undefined
      return {
        name: parsed.name,
        description: parsed.description,
        ...(parsed.whenToUse !== undefined ? { whenToUse: parsed.whenToUse } : {}),
        invocation: invocationFrom(parsed.metadata),
        source: SOURCE,
        provider: name,
        resourceBase: { kind: 'directory', path: candidate.locator },
        path: candidate.path,
        ...(Object.keys(parsed.metadata).length > 0 ? { metadata: parsed.metadata } : {}),
        content: parsed.content,
      }
    },
  }))
}

export { apply, name, inject }
export default { apply, name, inject }
