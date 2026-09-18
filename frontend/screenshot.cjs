const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 430, height: 900 },
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1'
  });
  const page = await context.newPage();
  
  const pages = [
    { name: '首页', page: 'create-home', file: 'screenshot-home.png' },
    { name: '任务列表', page: 'task-list', file: 'screenshot-tasks.png' },
    { name: '音色库', page: 'voice-library', file: 'screenshot-voices.png' },
    { name: '脚本输入', page: 'script-input', file: 'screenshot-script-input.png' },
    { name: 'AI改写', page: 'rewrite-review', file: 'screenshot-rewrite.png' },
    { name: '克隆音色', page: 'voice-clone', file: 'screenshot-clone.png' },
    { name: '配音生成', page: 'tts-generate', file: 'screenshot-tts.png' },
    { name: '视频上传', page: 'video-upload', file: 'screenshot-upload.png' },
    { name: '生成中', page: 'generating', file: 'screenshot-generating.png' },
    { name: '视频预览', page: 'video-preview', file: 'screenshot-preview.png' },
  ];
  
  for (const p of pages) {
    console.log(`正在截图${p.name}...`);
    await page.goto('http://localhost:5173/', { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);
    await page.evaluate((pageName) => { window.state.navigate(pageName); }, p.page);
    await page.waitForTimeout(1500);
    await page.screenshot({ path: p.file, fullPage: true });
    console.log(`✓ ${p.name}已保存: ${p.file}`);
  }
  
  await browser.close();
  console.log('\n✅ 所有截图完成!');
})();
