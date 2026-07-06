#!/usr/bin/env node
// 律师营销助手安装脚本

import { execSync } from 'child_process';
import { existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

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
    console.log('   ✅ Agent Reach 安装完成');
  } catch (e) {
    console.log('   ⚠️ Agent Reach 安装失败（不影响核心功能，热点追踪将使用备用搜索方案）');
    console.log(`      ${e.message}`);
  }

  // 4. 预下载嵌入模型
  console.log('📦 预下载嵌入模型 bge-base-zh-v1.5...');
  execSync('python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer(\'BAAI/bge-base-zh-v1.5\')"', { stdio: 'inherit' });

  // 5. 构建种子数据库
  console.log('📦 构建种子知识库...');
  execSync('python3 build-seed.py', { cwd: __dirname, stdio: 'inherit' });

  // 6. 输出完成
  console.log('\n✅ 安装完成！');
  console.log('📋 按以下步骤使用：');
  console.log('   1. 在 Codex 中创建新 Thread');
  console.log('   2. 开始使用（如："学习这个账号的风格"）');
}

main().catch(e => {
  console.error('❌ 安装失败:', e.message);
  process.exit(1);
});
