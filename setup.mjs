#!/usr/bin/env node
import { execSync } from 'child_process';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

console.log('🚀 正在安装律师营销助手...\n');

console.log('📦 检查 Python...');
const pythonVer = execSync('python3 --version', { encoding: 'utf-8' }).trim();
console.log(`   ✅ ${pythonVer}`);

console.log('📦 安装 Python 依赖...');
execSync('pip3 install -r requirements.txt', { cwd: __dirname, stdio: 'inherit' });

console.log('📦 预下载嵌入模型 bge-base-zh-v1.5...');
execSync('python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer(\'BAAI/bge-base-zh-v1.5\')"', { stdio: 'inherit' });

console.log('📦 构建种子知识库...');
execSync('python3 build-seed.py', { cwd: __dirname, stdio: 'inherit' });

console.log('\n✅ 安装完成！');
console.log('📋 按以下步骤使用：');
console.log('   1. 在 Codex 中创建新 Thread');
console.log('   2. 开始使用（如："学习这个账号的风格"）');
