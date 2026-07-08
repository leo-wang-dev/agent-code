const path = require('path');
const os = require('os');

module.exports = {
  apps: [
    {
      name: 'zylos-wechat',
      script: 'src/index.js',
      cwd: path.join(os.homedir(), 'zylos/.claude/skills/wechat'),
      env: {
        NODE_ENV: 'production',
        ZYLOS_WECHAT_DATA_DIR: path.join(os.homedir(), 'zylos/components/wechat'),
      },
      autorestart: true,
      max_restarts: 10,
      restart_delay: 5000,
      error_file: path.join(os.homedir(), 'zylos/components/wechat/logs/error.log'),
      out_file: path.join(os.homedir(), 'zylos/components/wechat/logs/out.log'),
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
    },
  ],
};
