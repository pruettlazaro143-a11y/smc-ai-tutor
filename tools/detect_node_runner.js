// tools/test_detect.py 调用：用网页版引擎（detector/smc-detect.js）处理同一批数据文件，输出 JSON 供比对。
// 用法：node tools/detect_node_runner.js 任务.json 输出.json
const fs = require('fs');
const path = require('path');
const SMC = require(path.join(__dirname, '..', 'detector', 'smc-detect.js'));
const jobs = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const out = jobs.map(job => {
  try {
    const [K, info] = SMC.parse(fs.readFileSync(job.file, 'utf8'));
    const R = SMC.detect(K, job.params);
    const sel = SMC.select(K, R, job.params.last);
    return { K, info, R, sel, zh: SMC.report(K, R, sel, info, 'zh'), en: SMC.report(K, R, sel, info, 'en') };
  } catch (e) {
    return { error: String(e.message || e) };
  }
});
fs.writeFileSync(process.argv[3], JSON.stringify(out));
