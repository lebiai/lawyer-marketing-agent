#!/usr/bin/env node
// 律师营销助手安装脚本

import { execSync } from 'child_process';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { existsSync } from 'fs';

const __dirname = dirname(fileURLToPath(import.meta.url));
const DISTILLER_DIR = join(__dirname, 'mcp', 'blogger-distiller');

async function main() {
  console.log('🚀 正在安装律师营销助手...\n');

  // 1. 检查 Python
  console.log('📦 检查 Python...');
  const pythonVer = execSync('python3 --version', { encoding: 'utf-8' }).trim();
  console.log(`   ✅ ${pythonVer}`);

  // 2. 安装 Python 依赖
  console.log('📦 安装 Python 依赖...');
  execSync('pip3 install -r requirements.txt', { cwd: __dirname, stdio: 'inherit' });

  // 3. 安装 Agent Reach（互联网能力）
  console.log('📦 安装 Agent Reach（互联网搜索能力）...');
  try {
    execSync('pipx install https://github.com/Panniantong/agent-reach/archive/main.zip 2>/dev/null || pip3 install https://github.com/Panniantong/agent-reach/archive/main.zip', { stdio: 'inherit' });
    execSync('agent-reach install --env=auto', { stdio: 'inherit' });
    console.log('   ✅ Agent Reach 安装完成');
  } catch (e) {
    console.log('   ⚠️ Agent Reach 安装失败（不影响核心功能，热点追踪将使用备用搜索方案）');
    console.log(`      ${e.message}`);
  }

  // 4. 克隆 blogger-distiller（竞品/对标账号分析引擎）
  console.log('📦 安装 blogger-distiller（竞品账号分析引擎）...');
  if (existsSync(DISTILLER_DIR)) {
    console.log('   已存在，执行 git pull 更新...');
    execSync('git pull origin main', { cwd: DISTILLER_DIR, stdio: 'inherit' });
  } else {
    execSync('git clone --depth 1 https://github.com/otter1101/blogger-distiller.git "' + DISTILLER_DIR + '"', { stdio: 'inherit' });
  }
  console.log('   ✅ blogger-distiller 安装完成');

  // 5. 安装 blogger-distiller 的依赖
  console.log('📦 安装 blogger-distiller 依赖...');
  try {
    execSync('pip3 install python-docx -q', { stdio: 'inherit' });
    console.log('   ✅ 依赖安装完成');
  } catch (e) {
    console.log('   ⚠️ 依赖安装失败: ' + e.message);
  }

  // 6. 预下载嵌入模型
  console.log('📦 预下载嵌入模型 bge-base-zh-v1.5...');
  execSync('python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer(\'BAAI/bge-base-zh-v1.5\')"', { stdio: 'inherit' });

  // 7. 构建种子数据库
  console.log('📦 构建种子知识库...');
  execSync('python3 build-seed.py', { cwd: __dirname, stdio: 'inherit' });

  // 8. 输出完成
  console.log('\n✅ 安装完成！');
  console.log('📋 按以下步骤使用：');
  console.log('   1. 在 Codex 中创建新 Thread');
  console.log('   2. 开始使用（如："学习这个账号的风格"）');
  console.log('   3. 说"分析XX账号"会自动引导开通分析师权限');
  console.log('      💡 需要开通分析权限请联系微信 iodun001');
}

main().catch(e => {
  console.error('❌ 安装失败:', e.message);
  process.exit(1);
});
