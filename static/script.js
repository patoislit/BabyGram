/**
 * BabyGram – script.js
 * =====================
 * Logika pre Feed (infinite scroll, like, komentáre),
 * Reels (snap scroll, ken burns, like),
 * Chat (Socket.IO real-time),
 * a pomocné funkcie.
 */

/* ═══════════════════════════════════════════════════════════════
   HELPERS
═══════════════════════════════════════════════════════════════ */

/** Formátuje číslo: 1234 → "1.2k" */
function fmtNum(n) {
  return n >= 1000 ? (n / 1000).toFixed(1) + 'k' : String(n);
}

/** Relatívny čas: "2 hod. dozadu" */
function timeAgo(str) {
  if (!str) return '';
  const diff = Math.floor((Date.now() - new Date(str).getTime()) / 1000);
  if (diff < 60)    return 'práve teraz';
  if (diff < 3600)  return `${Math.floor(diff/60)} min.`;
  if (diff < 86400) return `${Math.floor(diff/3600)} hod.`;
  return `${Math.floor(diff/86400)} dní`;
}

/* ═══════════════════════════════════════════════════════════════
   FEED
═══════════════════════════════════════════════════════════════ */

let feedPage    = 1;
let feedLoading = false;
let feedHasMore = true;

// ID príspevku pre aktívny komentárový panel
let activePostId = null;

/** Inicializácia feedu po načítaní stránky */
function initFeed() {
  const feedEl = document.getElementById('postFeed');
  if (!feedEl) return;
  fetchPosts();
  setupFeedScroll();
}

/** Načíta stránku príspevkov z API */
async function fetchPosts() {
  if (feedLoading || !feedHasMore) return;
  feedLoading = true;
  document.getElementById('feedLoading').classList.remove('hidden');

  try {
    const res  = await fetch(`/api/posts?page=${feedPage}`);
    const data = await res.json();
    data.posts.forEach(renderPost);
    feedHasMore = data.has_more;
    feedPage++;
  } catch (e) {
    console.error('Feed error:', e);
  } finally {
    feedLoading = false;
    document.getElementById('feedLoading').classList.add('hidden');
  }
}

/** Vygeneruje HTML kartu príspevku a vloží do DOM */
function renderPost(p) {
  const div = document.createElement('div');
  div.className = 'post-card';
  div.setAttribute('data-post-id', p.id);
  div.innerHTML = `
    <div class="post-header">
      <img src="${p.author_avatar}" alt="${p.author_name}" class="post-avatar"/>
      <div>
        <div class="post-author">${p.author_name}</div>
        <div class="post-time">${timeAgo(p.created_at)}</div>
      </div>
    </div>
    <div class="post-img-wrap">
      <img src="${p.image_url}" alt="${p.caption}" class="post-img" loading="lazy"
           ondblclick="handleLike(this, ${p.id})"/>
    </div>
    <div class="post-actions">
      <button class="like-btn ${p.is_liked ? 'liked' : ''}"
              onclick="handleLike(this, ${p.id})"
              data-liked="${p.is_liked ? 1 : 0}"
              data-count="${p.like_count}">
        <i class="bi bi-heart${p.is_liked ? '-fill' : ''}"></i>
        <span class="like-count">${fmtNum(p.like_count)}</span>
      </button>
      <button class="comment-btn" onclick="openCommentModal(${p.id})">
        <i class="bi bi-chat"></i>
        <span>${fmtNum(p.comment_count)}</span>
      </button>
    </div>
    <div class="post-caption">
      <strong>${p.author_name}</strong>${p.caption}
    </div>
  `;
  document.getElementById('postFeed').appendChild(div);
}

/** Infinite scroll pomocou IntersectionObserver */
function setupFeedScroll() {
  const sentinel = document.getElementById('feedSentinel');
  if (!sentinel) return;
  new IntersectionObserver(entries => {
    if (entries[0].isIntersecting) fetchPosts();
  }, { rootMargin: '200px' }).observe(sentinel);
}

/** Toggle like – aktualizuje UI a zavolá API */
async function handleLike(el, postId) {
  // El môže byť button alebo img (double-tap)
  const btn = el.classList.contains('like-btn')
    ? el
    : el.closest('.post-card').querySelector('.like-btn');

  const isLiked = btn.dataset.liked === '1';
  const newLiked = !isLiked;

  // Okamžitá aktualizácia UI (optimistic)
  btn.dataset.liked = newLiked ? '1' : '0';
  btn.classList.toggle('liked', newLiked);
  btn.querySelector('i').className = `bi bi-heart${newLiked ? '-fill' : ''}`;

  let count = parseInt(btn.dataset.count);
  count += newLiked ? 1 : -1;
  btn.dataset.count = count;
  btn.querySelector('.like-count').textContent = fmtNum(count);

  // Efekt vyletujúceho srdiečka
  if (newLiked) spawnHeart(btn.closest('.post-card'));

  // API call
  try {
    const res  = await fetch('/api/like', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ post_id: postId }),
    });
    const data = await res.json();
    btn.querySelector('.like-count').textContent = fmtNum(data.count);
    btn.dataset.count = data.count;
  } catch (e) { console.error('Like error:', e); }
}

/** Vytvorí efekt vyletujúceho srdiečka */
function spawnHeart(card) {
  const p = document.createElement('span');
  p.className = 'heart-particle';
  p.textContent = ['❤️','💖','💗','💕'][Math.floor(Math.random()*4)];
  card.style.position = 'relative';
  card.appendChild(p);
  setTimeout(() => p.remove(), 800);
}

/* ── Komentáre ─────────────────────────────────────────────────────────── */

function openCommentModal(postId) {
  activePostId = postId;
  document.getElementById('commentModal').classList.remove('hidden');
  document.getElementById('commentList').innerHTML = '';
  document.getElementById('commentInput').value = '';
  loadComments(postId);
  setTimeout(() => document.getElementById('commentInput').focus(), 350);
}

function closeCommentModal(e) {
  if (!e || e.target === document.getElementById('commentModal')) {
    document.getElementById('commentModal').classList.add('hidden');
    activePostId = null;
  }
}

async function loadComments(postId) {
  try {
    const res   = await fetch(`/api/comments/${postId}`);
    const items = await res.json();
    const list  = document.getElementById('commentList');
    if (!items.length) {
      list.innerHTML = '<div style="text-align:center;color:var(--text-light);padding:20px">Zatiaľ žiadne komentáre 🥹</div>';
      return;
    }
    list.innerHTML = items.map(c => `
      <div class="comment-item">
        <img src="${c.avatar}" alt="${c.username}"/>
        <div class="comment-body">
          <div class="comment-user">${c.username}</div>
          <div class="comment-text">${escHtml(c.text)}</div>
        </div>
      </div>
    `).join('');
  } catch(e) { console.error('Comments error:', e); }
}

async function submitComment() {
  if (!activePostId) return;
  const input = document.getElementById('commentInput');
  const text  = input.value.trim();
  if (!text) return;
  input.value = '';

  try {
    const res  = await fetch('/api/comment', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ post_id: activePostId, text }),
    });
    const data = await res.json();
    if (data.success) {
      // Pridaj komentár na vrch
      const list = document.getElementById('commentList');
      const el   = document.createElement('div');
      el.className = 'comment-item';
      el.innerHTML = `
        <div class="comment-body">
          <div class="comment-user">${data.username}</div>
          <div class="comment-text">${escHtml(data.text)}</div>
        </div>
      `;
      list.prepend(el);
    }
  } catch(e) { console.error('Comment submit error:', e); }
}

/* Escape HTML pre bezpečné vkladanie textu */
function escHtml(str) {
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

/* ═══════════════════════════════════════════════════════════════
   REELS
═══════════════════════════════════════════════════════════════ */

let reelsPage    = 1;
let reelsLoading = false;
let reelsHasMore = true;
let currentReelIndex = 0;

async function initReels() {
  const wrap = document.getElementById('reelsWrap');
  if (!wrap) return;
  await fetchReels();
  setupReelScroll();
  setupReelSentinel();
}

async function fetchReels() {
  if (reelsLoading || !reelsHasMore) return;
  reelsLoading = true;
  try {
    const res  = await fetch(`/api/reels?page=${reelsPage}`);
    const data = await res.json();
    data.reels.forEach(renderReel);
    reelsHasMore = data.has_more;
    reelsPage++;
  } catch(e) { console.error('Reels error:', e); }
  finally { reelsLoading = false; }
}

function renderReel(r) {
  const card = document.createElement('div');
  card.className = 'reel-card';
  card.setAttribute('data-reel-id', r.id);
  card.innerHTML = `
    <!-- Ken Burns background -->
    <div class="reel-bg" style="background-image:url('${r.image_url}')"></div>

    <!-- Akcie na pravej strane -->
    <div class="reel-actions">
      <div class="reel-avatar-wrap">
        <img src="${r.author_avatar}" alt="${r.author_name}"/>
      </div>
      <button class="reel-action-btn" onclick="handleReelLike(this)">
        <i class="bi bi-heart"></i>
        <span>${fmtNum(r.likes)}</span>
      </button>
      <button class="reel-action-btn" onclick="">
        <i class="bi bi-chat-dots"></i>
        <span>Komentár</span>
      </button>
    </div>

    <!-- Info dole -->
    <div class="reel-info">
      <div class="reel-author">@${r.author_name}</div>
      <div class="reel-caption">${r.caption}</div>
    </div>
  `;
  document.getElementById('reelsWrap').appendChild(card);
}

/** Snap scroll – animuje ken burns pri každom reeli */
function setupReelScroll() {
  const wrap = document.getElementById('reelsWrap');
  if (!wrap) return;

  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      const bg = entry.target.querySelector('.reel-bg');
      if (!bg) return;
      if (entry.isIntersecting) {
        // Reset animácie – reštartuje ken burns
        bg.style.animation = 'none';
        void bg.offsetHeight; // reflow
        bg.style.animation = '';
      }
    });
  }, { threshold: 0.6 });

  document.querySelectorAll('.reel-card').forEach(c => observer.observe(c));
}

/** Sentinel pre načítanie ďalších reels pri scrolle na koniec */
function setupReelSentinel() {
  const s = document.getElementById('reelsSentinel');
  if (!s) return;
  new IntersectionObserver(entries => {
    if (entries[0].isIntersecting) {
      fetchReels().then(setupReelScroll);
    }
  }, { rootMargin: '100px' }).observe(s);
}

function prevReel() {
  const cards = document.querySelectorAll('.reel-card');
  currentReelIndex = Math.max(0, currentReelIndex - 1);
  cards[currentReelIndex]?.scrollIntoView({ behavior: 'smooth' });
}

function nextReel() {
  const cards = document.querySelectorAll('.reel-card');
  currentReelIndex = Math.min(cards.length - 1, currentReelIndex + 1);
  cards[currentReelIndex]?.scrollIntoView({ behavior: 'smooth' });
}

function handleReelLike(btn) {
  const isLiked = btn.classList.toggle('liked');
  const span    = btn.querySelector('span');
  const icon    = btn.querySelector('i');
  icon.className = isLiked ? 'bi bi-heart-fill' : 'bi bi-heart';
  // Lokálny counter (bez DB pre reels – sú vzorové)
  let n = parseFloat(span.textContent) || 0;
  if (span.textContent.endsWith('k')) n *= 1000;
  span.textContent = fmtNum(Math.round(n) + (isLiked ? 1 : -1));
}

/* ═══════════════════════════════════════════════════════════════
   CHAT (Socket.IO)
═══════════════════════════════════════════════════════════════ */

let socket       = null;
let typingTimer  = null;

/** Inicializácia Socket.IO spojenia pre konkrétnu konverzáciu */
function initChat() {
  if (typeof CHAT_TARGET_ID === 'undefined') return;

  socket = io({ transports: ['websocket', 'polling'] });

  socket.on('connect', () => {
    socket.emit('join_chat', { target_id: CHAT_TARGET_ID });
  });

  // Príjem novej správy
  socket.on('new_message', (msg) => {
    appendMessage(msg);
    hideTypingIndicator();
  });

  // Indikátor písania
  socket.on('user_typing', (data) => {
    showTypingIndicator(data.username);
  });

  // Scroll na koniec pri otvorení
  scrollToBottom();
}

/** Odošle správu cez socket */
function chatSendMessage() {
  const input = document.getElementById('msgInput');
  if (!input) return;
  const text = input.value.trim();
  if (!text) return;
  input.value = '';

  // Zobrazí vlastnú správu okamžite (optimistic)
  appendMessage({
    sender_id: CURRENT_USER_ID,
    text,
    is_mine: true,
    created_at: new Date().toLocaleTimeString('sk-SK', { hour: '2-digit', minute: '2-digit' }),
  });

  if (socket) {
    socket.emit('send_message', { target_id: CHAT_TARGET_ID, text });
  }
}

function appendMessage(msg) {
  const area = document.getElementById('messagesArea');
  if (!area) return;
  const div = document.createElement('div');
  div.className = `msg-bubble ${msg.is_mine ? 'mine' : 'theirs'}`;
  div.innerHTML = `
    <div class="bubble-text">${escHtml(msg.text)}</div>
    <div class="bubble-time">${msg.created_at || ''}</div>
  `;
  area.appendChild(div);
  scrollToBottom();
}

function scrollToBottom() {
  const area = document.getElementById('messagesArea');
  if (area) area.scrollTop = area.scrollHeight;
}

let typingHideTimer = null;
function showTypingIndicator(username) {
  const el = document.getElementById('typingStatus');
  if (el) el.textContent = `${username} píše... ✍️`;
  clearTimeout(typingHideTimer);
  typingHideTimer = setTimeout(hideTypingIndicator, 3000);
}

function hideTypingIndicator() {
  const el = document.getElementById('typingStatus');
  if (el) el.textContent = 'online 🟢';
}

// Indikátor písania – odošle event pri každom stlačení klávesu
document.addEventListener('input', (e) => {
  if (e.target.id !== 'msgInput' || !socket) return;
  socket.emit('typing', { target_id: CHAT_TARGET_ID });
});

/* ═══════════════════════════════════════════════════════════════
   INICIALIZÁCIA podľa aktuálnej stránky
═══════════════════════════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
  const path = window.location.pathname;

  if (path === '/feed' || path === '/') {
    initFeed();
  }
  // Reels inicializácia je v reels.html cez extra_scripts blok
  // Chat inicializácia je priamo v chat.html šablóne
});
