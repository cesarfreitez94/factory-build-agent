import { createHash } from "node:crypto"
import { mkdir, readdir, readFile, writeFile, appendFile } from "node:fs/promises"
import { join, relative } from "node:path"

const OBSERVED_AGENTS_DIRECTORY = ".opencode/agents"
const OBSERVABILITY_DIRECTORY = ".factory/observability"

const CONFIG = {
  captureRawEvents: false,
  captureToolOutput: false,
  captureReasoningText: false,
  captureMessageText: false,
  captureAgentPromptSnapshots: true,
}

type TokenUsage = {
  input: number
  output: number
  reasoning: number
  cacheRead: number
  cacheWrite: number
}

type AgentIndexEntry = {
  name: string
  path: string
  description: string
  mode: string
  hidden: boolean
  promptHash: string
  fileHash: string
  promptSnapshot?: string
}

type AgentStats = {
  agent: string
  promptHash: string
  tokens: TokenUsage
  cost: number
  messages: number
  tools: Map<string, number>
  filesReadConfirmed: Set<string>
  filesReadProbable: Set<string>
  filesReadInferred: Set<string>
  filesEdited: Set<string>
  reasoningParts: number
  reasoningChars: number
}

type Invocation = {
  from: string
  to: string
  sessionID: string
  messageID: string
  description: string
  promptHash: string
}

type RootStats = {
  rootSessionID: string
  sessions: Set<string>
  agents: Map<string, AgentStats>
  invocations: Invocation[]
  ignoredInvocations: number
  unattributed: {
    tokens: TokenUsage
    cost: number
    reasons: Map<string, number>
  }
}

type MessageTotals = {
  agent: string
  rootSessionID: string
  tokens: TokenUsage
  cost: number
}

const zeroTokens = (): TokenUsage => ({
  input: 0,
  output: 0,
  reasoning: 0,
  cacheRead: 0,
  cacheWrite: 0,
})

const hashText = (value: string): string =>
  createHash("sha256").update(value).digest("hex").slice(0, 16)

const asNumber = (value: unknown): number => (typeof value === "number" ? value : 0)

const addTokens = (target: TokenUsage, delta: TokenUsage) => {
  target.input += delta.input
  target.output += delta.output
  target.reasoning += delta.reasoning
  target.cacheRead += delta.cacheRead
  target.cacheWrite += delta.cacheWrite
}

const subtractTokens = (left: TokenUsage, right: TokenUsage): TokenUsage => ({
  input: left.input - right.input,
  output: left.output - right.output,
  reasoning: left.reasoning - right.reasoning,
  cacheRead: left.cacheRead - right.cacheRead,
  cacheWrite: left.cacheWrite - right.cacheWrite,
})

const normalizeTokens = (value: any): TokenUsage => ({
  input: asNumber(value?.input),
  output: asNumber(value?.output),
  reasoning: asNumber(value?.reasoning),
  cacheRead: asNumber(value?.cache?.read ?? value?.cacheRead),
  cacheWrite: asNumber(value?.cache?.write ?? value?.cacheWrite),
})

const parseFrontmatterScalar = (frontmatter: string, key: string): string => {
  const match = frontmatter.match(new RegExp(`^${key}:\\s*(.*)$`, "m"))
  return match?.[1]?.trim().replace(/^["']|["']$/g, "") ?? ""
}

const parseAgentDefinition = (name: string, path: string, text: string): AgentIndexEntry => {
  const parts = text.split("---")
  const frontmatter = parts.length >= 3 ? parts[1] : ""
  const body = parts.length >= 3 ? parts.slice(2).join("---").trim() : text.trim()
  const hiddenValue = parseFrontmatterScalar(frontmatter, "hidden")

  return {
    name,
    path,
    description: parseFrontmatterScalar(frontmatter, "description"),
    mode: parseFrontmatterScalar(frontmatter, "mode") || "all",
    hidden: hiddenValue === "true",
    promptHash: hashText(body),
    fileHash: hashText(text),
    promptSnapshot: CONFIG.captureAgentPromptSnapshots ? body : undefined,
  }
}

const ensureDirectory = async (path: string) => {
  await mkdir(path, { recursive: true })
}

const writeJson = async (path: string, value: unknown) => {
  await ensureDirectory(path.substring(0, path.lastIndexOf("/")))
  await writeFile(path, `${JSON.stringify(value, null, 2)}\n`, "utf8")
}

const appendJsonLine = async (path: string, value: unknown) => {
  await ensureDirectory(path.substring(0, path.lastIndexOf("/")))
  await appendFile(path, `${JSON.stringify(value)}\n`, "utf8")
}

const eventPayload = (input: any): any => input?.event?.payload ?? input?.event ?? input?.payload ?? input

const eventType = (input: any): string => eventPayload(input)?.type ?? ""

const eventProperties = (input: any): any => eventPayload(input)?.properties ?? {}

const valueFromAnyKey = (input: any, keys: string[]): string | undefined => {
  for (const key of keys) {
    const value = input?.[key]
    if (typeof value === "string" && value.length > 0) return value
  }
  return undefined
}

const isLikelyFilePath = (token: string): boolean => {
  if (!token || token.length < 2) return false
  if (token.startsWith("-")) return false
  if (token.includes("=")) return false
  return /^\.{0,2}\/[^\s]+$/.test(token) || /\.[a-zA-Z]{2,6}$/.test(token)
}

const inferBashFiles = (command: string): string[] => {
  const results = new Set<string>()
  const matcher = /\b(?:cat|sed|rg|grep|head|tail|less|nl)\b\s+([^|;&]+)/g
  let match: RegExpExecArray | null

  while ((match = matcher.exec(command)) !== null) {
    for (const token of match[1].trim().split(/\s+/)) {
      const clean = token.replace(/^["']|["']$/g, "")
      if (!clean || !isLikelyFilePath(clean)) continue
      results.add(clean)
    }
  }

  return [...results]
}

const formatMoney = (value: number): string => {
  if (!Number.isFinite(value) || value === 0) return "0"
  return `$${value.toFixed(6)}`
}

export const FbaAgentObserver = async ({ worktree, directory, client }: any) => {
  const root = worktree ?? directory
  const observedAgentsPath = join(root, OBSERVED_AGENTS_DIRECTORY)
  const observabilityPath = join(root, OBSERVABILITY_DIRECTORY)
  const sessionPath = join(observabilityPath, "sessions")
  const reportsPath = join(observabilityPath, "reports")
  const rawEventsPath = join(observabilityPath, "raw-events.jsonl")
  const summaryPath = join(observabilityPath, "summary.json")
  const summaryPrevPath = join(observabilityPath, "summary.json.prev")

  const agentIndex = new Map<string, AgentIndexEntry>()
  const sessions = new Map<string, { id: string; parentID?: string; agent?: string }>()
  const messageAgents = new Map<string, string>()
  const messageTotals = new Map<string, MessageTotals>()
  const processedTokenMessages = new Set<string>()
  const rootStats = new Map<string, RootStats>()
  const processedTools = new Set<string>()

  const rebuildAgentIndex = async () => {
    agentIndex.clear()

    try {
      const files = await readdir(observedAgentsPath)
      for (const file of files.filter((item) => item.endsWith(".md")).sort()) {
        const absolutePath = join(observedAgentsPath, file)
        const text = await readFile(absolutePath, "utf8")
        const name = file.replace(/\.md$/, "")
        agentIndex.set(
          name,
          parseAgentDefinition(name, relative(root, absolutePath), text),
        )
      }

      await writeJson(join(observabilityPath, "agent-index.json"), {
        generatedAt: new Date().toISOString(),
        observedDirectory: OBSERVED_AGENTS_DIRECTORY,
        ignoredDirectory: "templates/.opencode/agents",
        agents: [...agentIndex.values()],
      })
    } catch (error) {
      await client?.app?.log?.({
        body: {
          service: "fba-agent-observer",
          level: "warn",
          message: "Could not rebuild agent index",
          extra: { error: String(error) },
        },
      })
    }
  }

  const isObservedAgent = (agent?: string): agent is string =>
    typeof agent === "string" && agentIndex.has(agent)

  const rootSessionID = (sessionID: string): string => {
    let current = sessionID
    const visited = new Set<string>()

    while (sessions.get(current)?.parentID && !visited.has(current)) {
      visited.add(current)
      current = sessions.get(current)?.parentID ?? current
    }

    return current
  }

  const getRootStats = (sessionID: string): RootStats => {
    const rootID = rootSessionID(sessionID)
    let stats = rootStats.get(rootID)

    if (!stats) {
      stats = {
        rootSessionID: rootID,
        sessions: new Set([rootID]),
        agents: new Map(),
        invocations: [],
        ignoredInvocations: 0,
        unattributed: {
          tokens: zeroTokens(),
          cost: 0,
          reasons: new Map(),
        },
      }
      rootStats.set(rootID, stats)
    }

    stats.sessions.add(sessionID)
    return stats
  }

  const getAgentStats = (stats: RootStats, agent: string): AgentStats => {
    let agentStats = stats.agents.get(agent)
    const indexed = agentIndex.get(agent)

    if (!agentStats) {
      agentStats = {
        agent,
        promptHash: indexed?.promptHash ?? "",
        tokens: zeroTokens(),
        cost: 0,
        messages: 0,
        tools: new Map(),
        filesReadConfirmed: new Set(),
        filesReadProbable: new Set(),
        filesReadInferred: new Set(),
        filesEdited: new Set(),
        reasoningParts: 0,
        reasoningChars: 0,
      }
      stats.agents.set(agent, agentStats)
    }

    return agentStats
  }

  const recordLedger = async (sessionID: string, value: Record<string, unknown>) => {
    const rootID = rootSessionID(sessionID)
    await appendJsonLine(join(sessionPath, `${rootID}.jsonl`), {
      recordedAt: new Date().toISOString(),
      rootSessionID: rootID,
      sessionID,
      ...value,
    })
  }

  const addUnattributed = async (
    sessionID: string,
    tokens: TokenUsage,
    cost: number,
    reason: string,
  ) => {
    const stats = getRootStats(sessionID)
    addTokens(stats.unattributed.tokens, tokens)
    stats.unattributed.cost += cost
    stats.unattributed.reasons.set(reason, (stats.unattributed.reasons.get(reason) ?? 0) + 1)
    await recordLedger(sessionID, { type: "unattributed_tokens", tokens, cost, reason })
  }

  const applyMessageTotals = async (message: any) => {
    if (message?.role !== "assistant" || !message?.id || !message?.sessionID) return

    const dedupKey = `${message.sessionID}:${message.id}`
    if (processedTokenMessages.has(dedupKey)) return
    processedTokenMessages.add(dedupKey)

    const agent = messageAgents.get(message.parentID) ?? sessions.get(message.sessionID)?.agent
    const tokens = normalizeTokens(message.tokens)
    const cost = asNumber(message.cost)
    const previous = messageTotals.get(message.id)

    if (previous) {
      const oldStats = getRootStats(previous.rootSessionID)
      if (isObservedAgent(previous.agent)) {
        const agentStats = getAgentStats(oldStats, previous.agent)
        addTokens(agentStats.tokens, subtractTokens(zeroTokens(), previous.tokens))
        agentStats.cost -= previous.cost
      } else {
        addTokens(oldStats.unattributed.tokens, subtractTokens(zeroTokens(), previous.tokens))
        oldStats.unattributed.cost -= previous.cost
      }
    }

    if (isObservedAgent(agent)) {
      const stats = getRootStats(message.sessionID)
      const agentStats = getAgentStats(stats, agent)
      addTokens(agentStats.tokens, tokens)
      agentStats.cost += cost
      agentStats.messages += previous ? 0 : 1
      messageTotals.set(message.id, {
        agent,
        rootSessionID: stats.rootSessionID,
        tokens,
        cost,
      })
      await recordLedger(message.sessionID, { type: "tokens", agent, messageID: message.id, tokens, cost })
    } else {
      await addUnattributed(message.sessionID, tokens, cost, "message_without_observed_agent")
      messageTotals.set(message.id, {
        agent: agent ?? "unknown",
        rootSessionID: rootSessionID(message.sessionID),
        tokens,
        cost,
      })
    }
  }

  const recordFileAccess = (agentStats: AgentStats, tool: string, input: any) => {
    const directPath = valueFromAnyKey(input, ["filePath", "path", "file", "filepath"])

    if (tool === "read" && directPath) agentStats.filesReadConfirmed.add(directPath)
    if (["write", "edit", "apply_patch"].includes(tool) && directPath) {
      agentStats.filesEdited.add(directPath)
    }
    if (["grep", "glob", "list"].includes(tool) && directPath) {
      agentStats.filesReadProbable.add(directPath)
    }
    if (tool === "bash" && typeof input?.command === "string") {
      for (const inferred of inferBashFiles(input.command)) {
        agentStats.filesReadInferred.add(inferred)
      }
    }
  }

  const recordToolPart = async (part: any) => {
    if (part?.type !== "tool" || !part?.sessionID || !part?.messageID || !part?.callID) return

    const agent = messageAgents.get(part.messageID) ?? sessions.get(part.sessionID)?.agent
    if (!isObservedAgent(agent)) return

    const status = part.state?.status
    if (!["completed", "error"].includes(status)) return

    const processKey = `${part.callID}:${status}`
    if (processedTools.has(processKey)) return

    const stats = getRootStats(part.sessionID)
    const agentStats = getAgentStats(stats, agent)
    const tool = String(part.tool ?? "unknown")
    const input = part.state?.input ?? {}

    processedTools.add(processKey)
    agentStats.tools.set(tool, (agentStats.tools.get(tool) ?? 0) + 1)
    recordFileAccess(agentStats, tool, input)

    await recordLedger(part.sessionID, {
      type: "tool",
      agent,
      messageID: part.messageID,
      callID: part.callID,
      tool,
      status,
      input: CONFIG.captureToolOutput ? input : undefined,
    })
  }

  const recordInvocation = async (part: any) => {
    const callee = part?.agent ?? part?.name
    const caller = messageAgents.get(part?.messageID) ?? sessions.get(part?.sessionID)?.agent ?? "unknown"

    if (!part?.sessionID || !part?.messageID) return

    const stats = getRootStats(part.sessionID)
    if (!isObservedAgent(callee)) {
      stats.ignoredInvocations += 1
      await recordLedger(part.sessionID, {
        type: "ignored_invocation",
        from: caller,
        reason: "callee_not_in_observed_agents",
      })
      return
    }

    if (!isObservedAgent(caller)) {
      await recordLedger(part.sessionID, {
        type: "observed_agent_invoked_by_unobserved_agent",
        to: callee,
      })
      return
    }

    const prompt = typeof part.prompt === "string" ? part.prompt : ""
    const invocation = {
      from: caller,
      to: callee,
      sessionID: part.sessionID,
      messageID: part.messageID,
      description: typeof part.description === "string" ? part.description : "",
      promptHash: hashText(prompt),
    }

    stats.invocations.push(invocation)
    await recordLedger(part.sessionID, { type: "invocation", ...invocation })
  }

  const recordReasoning = async (part: any) => {
    if (part?.type !== "reasoning" || !part?.sessionID || !part?.messageID) return

    const agent = messageAgents.get(part.messageID) ?? sessions.get(part.sessionID)?.agent
    if (!isObservedAgent(agent)) return

    const agentStats = getAgentStats(getRootStats(part.sessionID), agent)
    agentStats.reasoningParts += 1
    agentStats.reasoningChars += typeof part.text === "string" ? part.text.length : 0

    await recordLedger(part.sessionID, {
      type: "reasoning_visible",
      agent,
      messageID: part.messageID,
      chars: typeof part.text === "string" ? part.text.length : 0,
      text: CONFIG.captureReasoningText ? part.text : undefined,
    })
  }

  const recordMessage = async (message: any) => {
    if (!message?.id || !message?.sessionID) return

    if (message.role === "user" && isObservedAgent(message.agent)) {
      messageAgents.set(message.id, message.agent)
      sessions.set(message.sessionID, {
        ...(sessions.get(message.sessionID) ?? { id: message.sessionID }),
        agent: message.agent,
      })
      getAgentStats(getRootStats(message.sessionID), message.agent)
      await recordLedger(message.sessionID, {
        type: "message_agent",
        agent: message.agent,
        messageID: message.id,
        text: CONFIG.captureMessageText ? message.text : undefined,
      })
    }

    if (message.role === "assistant") {
      const agent = messageAgents.get(message.parentID) ?? sessions.get(message.sessionID)?.agent
      if (isObservedAgent(agent)) messageAgents.set(message.id, agent)
      await applyMessageTotals(message)
    }
  }

  const reportFor = async (rootID: string) => {
    const stats = rootStats.get(rootID)
    if (!stats) return

    const lines: string[] = []
    lines.push("# FBA Agent Observer Report")
    lines.push("")
    lines.push(`Generated: ${new Date().toISOString()}`)
    lines.push(`Root session: ${rootID}`)
    lines.push(`Observed directory: ${OBSERVED_AGENTS_DIRECTORY}`)
    lines.push(`Ignored directory: templates/.opencode/agents`)
    lines.push("")
    lines.push("## Cost by Agent")
    lines.push("")
    lines.push("| Agent | Prompt hash | Input | Output | Reasoning | Cache read | Cache write | Cost |")
    lines.push("|---|---:|---:|---:|---:|---:|---:|---:|")

    for (const agent of [...agentIndex.keys()].sort()) {
      const agentStats = stats.agents.get(agent)
      const tokens = agentStats?.tokens ?? zeroTokens()
      const promptHash = agentStats?.promptHash || agentIndex.get(agent)?.promptHash || ""
      lines.push(
        `| ${agent} | ${promptHash} | ${tokens.input} | ${tokens.output} | ${tokens.reasoning} | ${tokens.cacheRead} | ${tokens.cacheWrite} | ${formatMoney(agentStats?.cost ?? 0)} |`,
      )
    }

    lines.push("")
    lines.push("## Invocations")
    lines.push("")
    if (stats.invocations.length === 0) {
      lines.push("No observed agent-to-agent invocations were detected.")
    } else {
      lines.push("| From | To | Description | Prompt hash |")
      lines.push("|---|---|---|---:|")
      for (const call of stats.invocations) {
        lines.push(`| ${call.from} | ${call.to} | ${call.description || "-"} | ${call.promptHash} |`)
      }
    }

    lines.push("")
    lines.push("## Tools by Agent")
    lines.push("")
    for (const agent of [...agentIndex.keys()].sort()) {
      const agentStats = stats.agents.get(agent)
      const tools = agentStats ? [...agentStats.tools.entries()].sort() : []
      lines.push(`### ${agent}`)
      if (tools.length === 0) {
        lines.push("- No observed tool usage.")
      } else {
        for (const [tool, count] of tools) lines.push(`- ${tool}: ${count}`)
      }
      lines.push("")
    }

    lines.push("## Files by Agent")
    lines.push("")
    for (const agent of [...agentIndex.keys()].sort()) {
      const agentStats = stats.agents.get(agent)
      lines.push(`### ${agent}`)
      if (!agentStats) {
        lines.push("- No observed file activity.")
        lines.push("")
        continue
      }
      lines.push(`- Confirmed reads: ${[...agentStats.filesReadConfirmed].sort().join(", ") || "-"}`)
      lines.push(`- Probable reads: ${[...agentStats.filesReadProbable].sort().join(", ") || "-"}`)
      lines.push(`- Inferred reads: ${[...agentStats.filesReadInferred].sort().join(", ") || "-"}`)
      lines.push(`- Edits: ${[...agentStats.filesEdited].sort().join(", ") || "-"}`)
      lines.push("")
    }

    lines.push("## Attribution Notes")
    lines.push("")
    lines.push(`- Ignored invocations outside observed agents: ${stats.ignoredInvocations}`)
    lines.push(`- Unattributed input tokens: ${stats.unattributed.tokens.input}`)
    lines.push(`- Unattributed output tokens: ${stats.unattributed.tokens.output}`)
    lines.push(`- Unattributed reasoning tokens: ${stats.unattributed.tokens.reasoning}`)
    lines.push(`- Unattributed cost: ${formatMoney(stats.unattributed.cost)}`)
    for (const [reason, count] of [...stats.unattributed.reasons.entries()].sort()) {
      lines.push(`- ${reason}: ${count}`)
    }

    lines.push("")
    lines.push("## Trends")
    lines.push("")
    try {
      const prevContent = await readFile(join(observabilityPath, "summary.json.prev"), "utf8")
      const prev = JSON.parse(prevContent)
      const current = buildSummary()
      for (const agent of [...agentIndex.keys()].sort()) {
        const currAgent = current.agents[agent]
        const prevAgent = prev.agents?.[agent]
        if (currAgent && prevAgent) {
          const costDelta = currAgent.cost - prevAgent.cost
          const tokensDelta = (currAgent.tokens.input + currAgent.tokens.output) -
            (prevAgent.tokens.input + prevAgent.tokens.output)
          const messagesDelta = currAgent.messages - prevAgent.messages
          lines.push(`### ${agent}`)
          lines.push(`- Cost delta: ${costDelta >= 0 ? "+" : ""}${formatMoney(costDelta)}`)
          lines.push(`- Tokens delta: ${tokensDelta >= 0 ? "+" : ""}${tokensDelta}`)
          lines.push(`- Messages delta: ${messagesDelta >= 0 ? "+" : ""}${messagesDelta}`)
          lines.push("")
        }
      }
    } catch {
      lines.push("_No previous summary available for comparison._")
      lines.push("")
    }

    await writeFile(join(reportsPath, `${rootID}.md`), `${lines.join("\n")}\n`, "utf8")
  }

  const buildSummary = (): any => {
    const agentMetrics: Record<string, any> = {}

    for (const [agentName, agentEntry] of agentIndex.entries()) {
      let totalCost = 0
      let totalMessages = 0
      let totalInput = 0
      let totalOutput = 0
      let totalReasoning = 0
      let totalCacheRead = 0
      let totalCacheWrite = 0
      const toolCounts: Record<string, number> = {}
      const sessionsSet = new Set<string>()

      for (const [, stats] of rootStats.entries()) {
        const aStats = stats.agents.get(agentName)
        if (aStats) {
          totalCost += aStats.cost
          totalMessages += aStats.messages
          totalInput += aStats.tokens.input
          totalOutput += aStats.tokens.output
          totalReasoning += aStats.tokens.reasoning
          totalCacheRead += aStats.tokens.cacheRead
          totalCacheWrite += aStats.tokens.cacheWrite
          for (const [tool, count] of aStats.tools.entries()) {
            toolCounts[tool] = (toolCounts[tool] ?? 0) + count
          }
          for (const s of stats.sessions) sessionsSet.add(s)
        }
      }

      agentMetrics[agentName] = {
        promptHash: agentEntry.promptHash,
        sessions: sessionsSet.size,
        messages: totalMessages,
        cost: parseFloat(totalCost.toFixed(6)),
        tokens: {
          input: totalInput,
          output: totalOutput,
          reasoning: totalReasoning,
          cacheRead: totalCacheRead,
          cacheWrite: totalCacheWrite,
        },
        tools: toolCounts,
      }
    }

    return {
      generatedAt: new Date().toISOString(),
      agents: agentMetrics,
      totalSessions: rootStats.size,
    }
  }

  const saveSummary = async () => {
    try {
      const current = buildSummary()

      try {
        const prevContent = await readFile(summaryPath, "utf8")
        const prev = JSON.parse(prevContent)
        await writeFile(summaryPrevPath, JSON.stringify(prev, null, 2), "utf8")
      } catch {
      }

      await writeFile(summaryPath, JSON.stringify(current, null, 2), "utf8")
    } catch (error) {
      await client?.app?.log?.({
        body: {
          service: "fba-agent-observer",
          level: "warn",
          message: "Could not save summary",
          extra: { error: String(error) },
        },
      })
    }
  }

  await ensureDirectory(sessionPath)
  await ensureDirectory(reportsPath)
  await rebuildAgentIndex()

  return {
    event: async (input: any) => {
      const type = eventType(input)
      const properties = eventProperties(input)

      if (CONFIG.captureRawEvents) {
        await appendJsonLine(rawEventsPath, {
          recordedAt: new Date().toISOString(),
          type,
          properties,
        })
      }

      if (type === "file.watcher.updated" && properties.file?.includes(OBSERVED_AGENTS_DIRECTORY)) {
        await rebuildAgentIndex()
      }

      if (type === "session.created" || type === "session.updated") {
        const info = properties.info
        if (info?.id) {
          sessions.set(info.id, {
            ...(sessions.get(info.id) ?? { id: info.id }),
            parentID: info.parentID,
          })
          getRootStats(info.id)
          await recordLedger(info.id, {
            type,
            title: info.title,
            parentID: info.parentID,
          })
        }
      }

      if (type === "message.updated") {
        await recordMessage(properties.info)
      }

      if (type === "message.part.updated") {
        const part = properties.part
        if (part?.type === "tool") await recordToolPart(part)
        if (part?.type === "subtask" || part?.type === "agent") await recordInvocation(part)
        if (part?.type === "reasoning") await recordReasoning(part)
      }

      if (type === "session.idle" && properties.sessionID) {
        await reportFor(rootSessionID(properties.sessionID))
        await saveSummary()
      }
    },
  }
}
