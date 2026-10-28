<template>
  <div class="chat-page">
    <div class="chat-header">
      <h2>智能售后助手</h2>
      <p class="subtitle">与 AI 对话，快速解决售后问题</p>
    </div>

    <div class="chat-container">
      <div ref="scrollRef" class="chat-messages">
        <div v-if="messages.length === 0" class="empty-hint">
          <div class="hint-icon">🤖</div>
          <p>你好，我是售后助手</p>
          <p class="hint-sub">告诉我你的问题，例如："我买的巧克力化了，想退款"</p>
        </div>

        <div
          v-for="msg in messages"
          :key="msg.id"
          :class="['chat-bubble', msg.role]"
        >
          <div class="bubble-avatar">{{ msg.role === "user" ? "👤" : "🤖" }}</div>
          <div class="bubble-content">{{ msg.content }}</div>
        </div>

        <div v-if="loading" class="chat-bubble assistant">
          <div class="bubble-avatar">🤖</div>
          <div class="bubble-content typing">
            <span></span><span></span><span></span>
          </div>
        </div>
      </div>

      <form @submit.prevent="sendMsg" class="chat-input">
        <input
          v-model="inputText"
          type="text"
          placeholder="输入你的问题..."
          :disabled="loading"
          autocomplete="off"
        />
        <button type="submit" :disabled="loading || !inputText.trim()">
          发送
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from "vue"
import request from "../utils/request"

const messages = ref([])
const inputText = ref("")
const loading = ref(false)
const scrollRef = ref(null)

async function loadHistory() {
  try {
    const res = await request.get("/chat/history")
    if (res.success) {
      messages.value = res.data.messages
      scrollToBottom()
    }
  } catch (e) {
    console.error("loadHistory error", e)
  }
}

async function sendMsg() {
  const text = inputText.value.trim()
  if (!text || loading.value) return

  const tempUserMsg = {
    id: Date.now(),
    role: "user",
    content: text,
  }
  messages.value.push(tempUserMsg)
  inputText.value = ""
  loading.value = true
  scrollToBottom()

  try {
    const res = await request.post("/chat/message", { content: text })
    if (res.success) {
      messages.value.push(res.data.assistant_message)
      scrollToBottom()
    }
  } catch (e) {
    console.error("sendMsg error", e)
    messages.value.push({
      id: Date.now() + 1,
      role: "assistant",
      content: "抱歉，服务暂时不可用，请稍后再试。",
    })
    scrollToBottom()
  } finally {
    loading.value = false
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (scrollRef.value) {
      scrollRef.value.scrollTop = scrollRef.value.scrollHeight
    }
  })
}

onMounted(loadHistory)
</script>

<style scoped>
.chat-page {
  max-width: 760px;
  margin: 0 auto;
  padding: 24px 16px;
  display: flex;
  flex-direction: column;
  height: calc(100vh - 64px);
  box-sizing: border-box;
}

.chat-header {
  text-align: center;
  margin-bottom: 16px;
  flex-shrink: 0;
}

.chat-header h2 {
  margin: 0;
  font-size: 22px;
  color: #1f2937;
}

.chat-header .subtitle {
  margin: 4px 0 0;
  color: #6b7280;
  font-size: 14px;
}

.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #f9fafb;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  overflow: hidden;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.empty-hint {
  text-align: center;
  color: #9ca3af;
  margin-top: 40px;
}

.empty-hint .hint-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.empty-hint p {
  margin: 4px 0;
}

.empty-hint .hint-sub {
  font-size: 13px;
}

.chat-bubble {
  display: flex;
  gap: 8px;
  max-width: 85%;
}

.chat-bubble.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.chat-bubble.assistant {
  align-self: flex-start;
}

.bubble-avatar {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  background: #e5e7eb;
}

.chat-bubble.user .bubble-avatar {
  background: #6366f1;
}

.bubble-content {
  padding: 10px 14px;
  border-radius: 12px;
  background: #fff;
  font-size: 14px;
  line-height: 1.5;
  color: #1f2937;
  white-space: pre-wrap;
  word-break: break-word;
}

.chat-bubble.user .bubble-content {
  background: #6366f1;
  color: #fff;
  border-bottom-right-radius: 4px;
}

.chat-bubble.assistant .bubble-content {
  border-bottom-left-radius: 4px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}

.typing {
  display: flex;
  gap: 3px;
  align-items: center;
  padding: 12px 16px !important;
}

.typing span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #9ca3af;
  animation: bounce 1.2s infinite ease-in-out;
}

.typing span:nth-child(2) { animation-delay: 0.15s; }
.typing span:nth-child(3) { animation-delay: 0.3s; }

@keyframes bounce {
  0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
  40% { transform: translateY(-4px); opacity: 1; }
}

.chat-input {
  display: flex;
  gap: 8px;
  padding: 12px;
  background: #fff;
  border-top: 1px solid #e5e7eb;
  flex-shrink: 0;
}

.chat-input input {
  flex: 1;
  padding: 10px 14px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.15s;
}

.chat-input input:focus {
  border-color: #6366f1;
}

.chat-input button {
  padding: 10px 20px;
  background: #6366f1;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.15s;
}

.chat-input button:hover:not(:disabled) {
  background: #4f46e5;
}

.chat-input button:disabled {
  background: #c7d2fe;
  cursor: not-allowed;
}
</style>