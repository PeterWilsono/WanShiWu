<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import affirmations from '../constants/affirmations.json'
import AppIcon from '../components/AppIcon.vue'
import AssistantComposer from '../components/AssistantComposer.vue'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const todayLabel = new Intl.DateTimeFormat('zh-CN', {
  month: 'long', day: 'numeric', weekday: 'long',
}).format(new Date())
const firstName = computed(() => authStore.user?.username || '朋友')
const affirmationIndex = ref(Math.floor(Math.random() * affirmations.length))
const affirmation = computed(() => affirmations[affirmationIndex.value])

function shuffleAffirmation(): void {
  if (affirmations.length < 2) return
  let next = affirmationIndex.value
  while (next === affirmationIndex.value) next = Math.floor(Math.random() * affirmations.length)
  affirmationIndex.value = next
}

const modules = [
  { name: 'todos', index: '01', icon: 'check', title: '待办清单', english: 'TO DO', description: '把脑海里的待办轻轻放下，专注眼前的一件事。', meta: '清单 · 重复 · 标签', tone: 'sage' },
  { name: 'calendar', index: '02', icon: 'calendar', title: '时间花园', english: 'CALENDAR', description: '日程与截止时间同屏生长，看见生活的从容节奏。', meta: '日程 · 月历 · 提醒', tone: 'clay' },
  { name: 'transactions', index: '03', icon: 'wallet', title: '收支手帖', english: 'LEDGER', description: '留下每一笔生活的注脚，让消费变得清晰可见。', meta: '记账 · 分类 · 精确到分', tone: 'ink' },
  { name: 'stats', index: '04', icon: 'chart', title: '月度回望', english: 'INSIGHTS', description: '从数字里读懂这个月，为下一次选择留一盏灯。', meta: '趋势 · 占比 · 结余', tone: 'gold' },
  { name: 'pantry', index: '05', icon: 'pantry', title: '食材书房', english: 'PANTRY', description: '照料每一份新鲜，先到期先使用，减少无意浪费。', meta: '库存 · 临期 · 购物', tone: 'sage' },
  { name: 'categories', index: '06', icon: 'settings', title: '分类雅集', english: 'CATEGORIES', description: '按照自己的生活方式，定制收入的来处与支出的去向。', meta: '自定义 · 内置保护', tone: 'clay' },
  { name: 'inbox', index: '07', icon: 'bookmark', title: '阅读收藏室', english: 'LIBRARY', description: '收好值得回看的文字，让链接沉淀为自己的知识手帖。', meta: '收藏 · 摘要 · 每周回顾', tone: 'gold' },
  { name: 'trip', index: '08', icon: 'transport', title: '远行手帖', english: 'JOURNEYS', description: '把想去的地方写进日程，让预算与每一天都从容有序。', meta: '行程 · 预算 · AI 草稿', tone: 'sage' },
]
</script>

<template>
  <main class="home">
    <section class="hero" aria-labelledby="hero-title">
      <div class="hero__copy">
        <p class="hero__eyebrow"><span />{{ todayLabel }} · 见字如面</p>
        <h1 id="hero-title">把生活的细碎，<br />安放得<em>井井有条。</em></h1>
        <p class="hero__intro">你好，{{ firstName }}。这里收藏你的计划、账目与日常灵感，<br class="desktop-only" />让每一件小事，都有恰好的位置。</p>
        <button class="hero__scroll" @click="router.push({ name: 'todos' })">
          开始整理今天 <span><AppIcon name="arrow" :size="18" /></span>
        </button>
      </div>

      <div class="hero-art">
        <span class="hero-art__orbit orbit-one" /><span class="hero-art__orbit orbit-two" />
        <div class="hero-art__sun">万</div>
        <div class="day-note">
          <div class="day-note__top"><span>万事屋小签</span><small>DAILY NOTES</small></div>
          <p class="day-note__date">{{ affirmation }}</p>
          <div class="day-note__line"><i /><span>给未来留一点时间</span></div>
          <div class="day-note__line"><i /><span>为此刻留一点专注</span></div>
          <div class="day-note__footer">
            <button class="day-note__refresh" aria-label="换一句万事屋小签" @click="shuffleAffirmation">
              <AppIcon name="sparkle" :size="13" />换一句
            </button><b>∞</b>
          </div>
        </div>
        <div class="floating-note floating-note--top"><AppIcon name="check" :size="16" /><span>小事，也有着落</span></div>
        <div class="floating-note floating-note--bottom"><AppIcon name="sparkle" :size="16" /><span>日常，自有秩序</span></div>
      </div>
    </section>

    <section class="assistant-section" aria-label="智能生活助手">
      <div class="assistant-section__intro">
        <p class="section-kicker">YOUR EVERYDAY ASSISTANT</p>
        <h2>一句话，<br />整理一个念头。</h2>
        <p>不用适应复杂的表单。把想法自然地说出来，确认之后，我们再替你安放。</p>
        <div class="privacy-note"><AppIcon name="sparkle" :size="16" /><span>先确认，后写入。决定始终在你。</span></div>
      </div>
      <div class="assistant-section__composer"><AssistantComposer /></div>
    </section>

    <section class="modules-section" aria-labelledby="modules-title">
      <header class="section-heading">
        <div><p class="section-kicker">A PLACE FOR EVERYTHING</p><h2 id="modules-title">生活，各有归处</h2></div>
        <p>八间小小的生活房间，<br />收好每一种日常。</p>
      </header>
      <div class="module-grid">
        <button
          v-for="module in modules"
          :key="module.name"
          class="module-card"
          :class="`module-card--${module.tone}`"
          @click="router.push({ name: module.name })"
        >
          <span class="module-card__top"><small>{{ module.index }} / {{ module.english }}</small><AppIcon :name="module.icon" :size="23" /></span>
          <span class="module-card__body"><strong>{{ module.title }}</strong><span>{{ module.description }}</span></span>
          <span class="module-card__footer"><small>{{ module.meta }}</small><i><AppIcon name="arrow" :size="18" /></i></span>
        </button>
      </div>
    </section>

    <footer class="home-footer">
      <span class="home-footer__seal">万</span>
      <p>认真对待日常，日常便会回馈以温柔。</p>
      <small>WANSHIWU · YOUR PERSONAL LIFE ATELIER</small>
    </footer>
  </main>
</template>

<style scoped>
.home { width: min(1360px, 100%); margin: 0 auto; padding: 0 40px; overflow: hidden; }
.hero { display: grid; min-height: 660px; grid-template-columns: 1.15fr .85fr; align-items: center; gap: 40px; padding: 74px 3% 88px; }
.hero__copy { position: relative; z-index: 2; animation: rise-in .8s both; }
.hero__eyebrow { display: flex; align-items: center; gap: 10px; margin-bottom: 30px; color: var(--ink-muted); font-size: 12px; font-weight: 550; letter-spacing: .12em; }
.hero__eyebrow span { width: 26px; height: 1px; background: var(--vermilion); }
.hero h1 { color: var(--ink); font-family: var(--font-display); font-size: clamp(45px, 4.5vw, 72px); font-weight: 500; line-height: 1.34; letter-spacing: -.07em; }
.hero h1 em { position: relative; color: var(--vermilion); font-style: normal; white-space: nowrap; }
.hero h1 em::after { position: absolute; right: 3px; bottom: -7px; left: 6px; height: 7px; border-top: 1px solid currentColor; border-radius: 50%; content: ''; opacity: .45; transform: rotate(-2deg); }
.hero__intro { margin-top: 30px; color: var(--ink-secondary); font-size: 15px; line-height: 2; }
.hero__scroll { display: inline-flex; align-items: center; gap: 18px; margin-top: 36px; padding: 0; border: 0; color: var(--ink); background: transparent; cursor: pointer; font-size: 14px; font-weight: 600; letter-spacing: .05em; }
.hero__scroll span { display: grid; width: 42px; height: 42px; place-items: center; border: 1px solid var(--ink); border-radius: 50%; transition: color .25s ease, background .25s ease, transform .25s ease; }
.hero__scroll:hover span { color: var(--paper-light); background: var(--ink); transform: translateX(4px); }
.hero-art { position: relative; width: min(100%, 470px); aspect-ratio: 1; justify-self: center; animation: rise-in 1s .12s both; }
.hero-art::before { position: absolute; inset: 12%; border-radius: 50%; background: #e4e7d9; content: ''; }
.hero-art__orbit { position: absolute; border: 1px solid rgb(24 59 50 / 13%); border-radius: 50%; }
.orbit-one { inset: 2%; transform: rotate(20deg) scaleY(.76); }
.orbit-two { inset: 8%; transform: rotate(-40deg) scaleY(.84); }
.hero-art__sun { position: absolute; top: 6%; right: 9%; display: grid; width: 62px; height: 62px; place-items: center; border-radius: 50%; color: var(--paper-light); background: var(--vermilion); box-shadow: 0 14px 30px rgb(196 91 63 / 20%); font-family: var(--font-display); font-size: 30px; }
.day-note { position: absolute; top: 18%; left: 18%; width: 64%; padding: 30px; border: 1px solid rgb(24 59 50 / 12%); border-radius: 4px 22px 4px 4px; background: #fbf9f1; box-shadow: 18px 24px 50px rgb(46 55 43 / 12%); transform: rotate(-4deg); transition: transform .5s cubic-bezier(.2,.8,.2,1); }
.hero-art:hover .day-note { transform: rotate(-1deg) translateY(-5px); }
.day-note::before { position: absolute; top: -9px; left: 38%; width: 74px; height: 23px; background: rgb(211 195 155 / 50%); content: ''; transform: rotate(3deg); }
.day-note__top { display: flex; align-items: baseline; justify-content: space-between; padding-bottom: 16px; border-bottom: 1px solid var(--line); }
.day-note__top span { font-family: var(--font-display); font-size: 17px; }
.day-note__top small { color: var(--ink-muted); font-size: 7px; letter-spacing: .2em; }
.day-note__date { min-height: 3.1em; padding: 26px 0; color: var(--ink); font-family: var(--font-display); font-size: clamp(24px, 2.2vw, 31px); line-height: 1.55; letter-spacing: .06em; }
.day-note__line { display: flex; align-items: center; gap: 10px; margin: 15px 0; color: var(--ink-secondary); font-size: 11px; }
.day-note__line i { width: 9px; height: 9px; border: 1px solid var(--sage); border-radius: 50%; }
.day-note__footer { display: flex; align-items: flex-end; justify-content: space-between; margin-top: 26px; padding-top: 14px; border-top: 1px solid var(--line-soft); color: var(--ink-muted); }
.day-note__footer span { font-size: 7px; letter-spacing: .2em; }
.day-note__footer b { color: var(--vermilion); font-family: var(--font-display); font-size: 24px; font-weight: 400; }
.day-note__refresh { display: inline-flex; align-items: center; gap: 5px; padding: 5px 0; border: 0; color: var(--ink-muted); background: transparent; cursor: pointer; font-size: 10px; letter-spacing: .08em; }
.day-note__refresh:hover { color: var(--vermilion); }
.floating-note { position: absolute; display: flex; align-items: center; gap: 8px; padding: 11px 15px; border: 1px solid var(--line-soft); border-radius: 12px; color: var(--ink-secondary); background: rgb(251 250 246 / 90%); box-shadow: var(--shadow-soft); font-size: 11px; backdrop-filter: blur(8px); animation: float 5s ease-in-out infinite; }
.floating-note--top { top: 22%; left: 0; }
.floating-note--bottom { right: 0; bottom: 18%; animation-delay: -2.5s; }
.assistant-section { position: relative; display: grid; grid-template-columns: .72fr 1.28fr; gap: 64px; margin: 0 calc(3% - 12px); padding: 60px; border-radius: 4px 44px 4px 4px; color: #f4f1e9; background: var(--ink); box-shadow: 0 30px 70px rgb(24 59 50 / 14%); }
.assistant-section::after { position: absolute; right: 24px; bottom: 22px; width: 64px; height: 64px; border-right: 1px solid rgb(255 255 255 / 12%); border-bottom: 1px solid rgb(255 255 255 / 12%); content: ''; }
.section-kicker { color: var(--vermilion); font-size: 10px; font-weight: 700; letter-spacing: .22em; }
.assistant-section__intro h2 { margin-top: 20px; font-family: var(--font-display); font-size: clamp(31px, 3vw, 43px); font-weight: 500; line-height: 1.5; }
.assistant-section__intro > p:not(.section-kicker) { max-width: 330px; margin-top: 22px; color: rgb(244 241 233 / 66%); font-size: 13px; line-height: 1.9; }
.privacy-note { display: flex; align-items: center; gap: 9px; margin-top: 34px; color: #c8d2c5; font-size: 11px; }
.assistant-section__composer { align-self: center; min-width: 0; padding: 30px; border-radius: 20px 20px 20px 4px; color: var(--ink); background: var(--paper-light); box-shadow: 0 18px 45px rgb(0 0 0 / 12%); }
.modules-section { padding: 110px 3% 90px; }
.section-heading { display: flex; align-items: flex-end; justify-content: space-between; gap: 30px; margin-bottom: 42px; }
.section-heading h2 { margin-top: 12px; font-family: var(--font-display); font-size: clamp(34px, 3.5vw, 48px); font-weight: 500; letter-spacing: -.04em; }
.section-heading > p { color: var(--ink-muted); font-size: 13px; line-height: 1.8; text-align: right; }
.module-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 18px; }
.module-card { position: relative; display: flex; min-height: 300px; flex-direction: column; justify-content: space-between; overflow: hidden; padding: 28px; border: 1px solid var(--line-soft); border-radius: 3px 24px 3px 3px; color: var(--ink); background: var(--paper-light); cursor: pointer; text-align: left; transition: border-color .3s ease, box-shadow .3s ease, transform .3s cubic-bezier(.2,.8,.2,1); }
.module-card::before { position: absolute; right: -60px; bottom: -80px; width: 180px; height: 180px; border-radius: 50%; background: var(--card-tint); content: ''; opacity: .4; transition: transform .45s ease; }
.module-card--sage { --card-tint: #cbd6c3; --card-accent: #56735f; }
.module-card--clay { --card-tint: #ecd0bf; --card-accent: #b45e44; }
.module-card--ink { --card-tint: #bfd0c8; --card-accent: #31594b; }
.module-card--gold { --card-tint: #e6d6b4; --card-accent: #9b783b; }
.module-card:hover { border-color: var(--line); box-shadow: var(--shadow-lift); transform: translateY(-6px); }
.module-card:hover::before { transform: scale(1.35); }
.module-card__top, .module-card__footer { position: relative; display: flex; align-items: center; justify-content: space-between; }
.module-card__top { color: var(--card-accent); }
.module-card__top small { font-size: 9px; font-weight: 650; letter-spacing: .17em; }
.module-card__body { position: relative; display: grid; gap: 15px; margin: 30px 0; }
.module-card__body strong { font-family: var(--font-display); font-size: 28px; font-weight: 600; letter-spacing: .04em; }
.module-card__body > span { max-width: 280px; color: var(--ink-secondary); font-size: 13px; line-height: 1.8; }
.module-card__footer small { color: var(--ink-muted); font-size: 10px; letter-spacing: .06em; }
.module-card__footer i { display: grid; width: 38px; height: 38px; place-items: center; border: 1px solid var(--line); border-radius: 50%; color: var(--card-accent); font-style: normal; transition: color .25s ease, background .25s ease; }
.module-card:hover .module-card__footer i { color: var(--paper-light); background: var(--card-accent); }
.home-footer { display: flex; flex-direction: column; align-items: center; padding: 45px 20px 70px; border-top: 1px solid var(--line); text-align: center; }
.home-footer__seal { display: grid; width: 32px; height: 32px; place-items: center; margin-bottom: 18px; border: 1px solid var(--vermilion); color: var(--vermilion); font-family: var(--font-display); transform: rotate(-4deg); }
.home-footer p { font-family: var(--font-display); font-size: 17px; letter-spacing: .1em; }
.home-footer small { margin-top: 14px; color: var(--ink-muted); font-size: 8px; letter-spacing: .22em; }
@keyframes rise-in { from { opacity: 0; transform: translateY(22px); } to { opacity: 1; transform: translateY(0); } }
@keyframes float { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-8px); } }
@media (max-width: 1050px) {
  .hero { min-height: 600px; padding-right: 0; padding-left: 0; }
  .assistant-section { gap: 36px; margin: 0; padding: 42px; }
  .modules-section { padding-right: 0; padding-left: 0; }
  .module-card { min-height: 280px; padding: 24px; }
}
@media (max-width: 820px) {
  .home { padding: 0 24px; }
  .hero { grid-template-columns: 1fr; padding-top: 64px; text-align: center; }
  .hero__eyebrow, .hero__scroll { justify-content: center; }
  .hero-art { width: min(100%, 400px); margin-top: 12px; }
  .assistant-section { grid-template-columns: 1fr; padding: 38px; }
  .assistant-section__intro > p:not(.section-kicker) { max-width: none; }
  .privacy-note { margin-top: 22px; }
  .module-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 560px) {
  .home { padding: 0 18px; }
  .hero { min-height: auto; gap: 24px; padding: 50px 0 60px; text-align: left; }
  .hero__eyebrow { justify-content: flex-start; margin-bottom: 22px; font-size: 10px; }
  .hero h1 { font-size: clamp(39px, 11.6vw, 56px); line-height: 1.42; }
  .hero__intro { margin-top: 24px; font-size: 13px; }
  .desktop-only { display: none; }
  .hero__scroll { margin-top: 28px; }
  .hero-art { width: 100%; max-width: 360px; }
  .day-note { padding: 24px; }
  .day-note__date { font-size: 25px; }
  .floating-note--top { left: -4px; }
  .floating-note--bottom { right: -4px; }
  .assistant-section { gap: 28px; padding: 30px 20px 20px; border-radius: 3px 28px 3px 3px; }
  .assistant-section__intro h2 { font-size: 30px; }
  .assistant-section__composer { padding: 20px 16px; }
  .modules-section { padding: 76px 0 64px; }
  .section-heading { align-items: flex-start; margin-bottom: 28px; }
  .section-heading > p { display: none; }
  .module-grid { grid-template-columns: 1fr; gap: 14px; }
  .module-card { min-height: 245px; padding: 25px; }
  .module-card__body { margin: 22px 0; }
  .home-footer p { font-size: 14px; }
}
</style>
