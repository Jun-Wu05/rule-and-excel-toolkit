// verify.mjs — repository CI gate.
import { readFile } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const root = dirname(fileURLToPath(import.meta.url))
const errors = []
const fail = (msg) => errors.push(msg)

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

  try {
    const changelog = await readFile(join(root, 'CHANGELOG.md'), 'utf8')
    const latest = /^## \[([^\]]+)\]/m.exec(changelog)?.[1]
    if (latest && latest !== pkg.version) fail(`package version ${pkg.version} != latest CHANGELOG version ${latest}`)
  } catch {
    fail('cannot read CHANGELOG.md')
  }
}

const providerUrl = pathToFileURL(join(root, 'lib', 'index.js')).href
try {
  const mod = await import(providerUrl)
  if (typeof mod.apply !== 'function') fail('lib/index.js must export apply()')
  if (!Array.isArray(mod.inject) || !mod.inject.includes('skills')) fail('lib/index.js must inject ["skills"]')
  if (typeof mod.name !== 'string') fail('lib/index.js must export a "name" string')
} catch (e) {
  fail(`lib/index.js failed to import: ${e.message}`)
}

const skillDir = join(root, 'skills', 'rule-and-excel-toolkit')
const skillFile = join(skillDir, 'SKILL.md')
const scriptsDir = join(skillDir, 'scripts')
for (const required of [
  skillFile,
  join(scriptsDir, 'toolkit.py'),
  join(scriptsDir, 'common', 'registry.py'),
  join(scriptsDir, 'common', 'result.py'),
  join(scriptsDir, 'common', 'output.py'),
  join(skillDir, 'references', 'cli-contract.md'),
]) {
  if (!existsSync(required)) fail(`required unified CLI file missing: ${required}`)
}

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

  const referenced = [...skillText.matchAll(/scripts\/([\w./-]+\.py)/g)].map((m) => m[1])
  for (const f of new Set(referenced)) {
    if (!existsSync(join(scriptsDir, f))) fail(`SKILL.md references missing script: ${f}`)
  }
}

if (errors.length > 0) {
  console.error('verify failed:')
  for (const e of errors) console.error('  - ' + e)
  process.exit(1)
}
console.log('verify ok: skill bundle and unified CLI contract are valid')
