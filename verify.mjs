// verify.mjs — CI gate for the rule-and-excel-toolkit-dsh bundle.
// Checks that the package is a loadable DSH skill bundle carrying one valid
// skill. Run with `node verify.mjs`; a non-zero exit fails the gate.
import { readFile } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const root = dirname(fileURLToPath(import.meta.url))
const errors = []
const fail = (msg) => errors.push(msg)

// 1. package.json declares a DSH bundle patch.
let pkg = null
try {
  pkg = JSON.parse(await readFile(join(root, 'package.json'), 'utf8'))
} catch {
  fail('package.json missing or invalid JSON')
}

if (pkg) {
  const patch = pkg.dsh?.bundle?.patch
  if (!patch) fail('package.json missing dsh.bundle.patch')
  else if (!existsSync(join(root, patch))) fail(`dsh.bundle.patch target missing: ${patch}`)
  if (pkg.type !== 'module') fail('package.json "type" must be "module"')
  if (!Array.isArray(pkg.files) || !pkg.files.includes('skills')) fail('package.json "files" must include "skills"')
}

// 2. the provider module loads and declares inject ['skills'].
const providerUrl = pathToFileURL(join(root, 'lib', 'index.js')).href
try {
  const mod = await import(providerUrl)
  if (typeof mod.apply !== 'function') fail('lib/index.js must export apply()')
  if (!Array.isArray(mod.inject) || !mod.inject.includes('skills')) fail('lib/index.js must inject ["skills"]')
  if (typeof mod.name !== 'string') fail('lib/index.js must export a "name" string')
} catch (e) {
  fail(`lib/index.js failed to import: ${e.message}`)
}

// 3. the single skill bundle and every script its body references.
const skillDir = join(root, 'skills', 'rule-and-excel-toolkit')
const skillFile = join(skillDir, 'SKILL.md')
if (!existsSync(skillFile)) fail('skills/rule-and-excel-toolkit/SKILL.md missing')

let skillText = ''
try {
  skillText = await readFile(skillFile, 'utf8')
} catch {
  fail('cannot read SKILL.md')
}

if (skillText) {
  if (!skillText.startsWith('---')) fail('SKILL.md missing YAML frontmatter')
  const name = (/^name:\s*"?([^"\n]+)"?[ \t]*$/m.exec(skillText)?.[1] ?? '').trim()
  const desc = (/^description:\s*(.+)$/m.exec(skillText)?.[1] ?? '').trim()
  if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(name)) fail(`SKILL.md name not kebab-case: "${name}"`)
  if (name !== 'rule-and-excel-toolkit') fail(`SKILL.md name mismatch: "${name}"`)
  if (!desc) fail('SKILL.md description empty')

  const scriptsDir = join(skillDir, 'scripts')
  const referenced = [...skillText.matchAll(/scripts\/([\w.-]+\.py)/g)].map((m) => m[1])
  for (const f of new Set(referenced)) {
    if (!existsSync(join(scriptsDir, f))) fail(`SKILL.md references missing script: ${f}`)
  }
}

if (errors.length > 0) {
  console.error('verify failed:')
  for (const e of errors) console.error('  - ' + e)
  process.exit(1)
}
console.log('verify ok: rule-and-excel-toolkit-dsh bundle is valid')
