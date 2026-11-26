# voxt-echo-test

一次录完的会议回声测试：Mac 外放"对方"（系统音轨），手机外放"自己"（麦克风音轨），两边同步播放，用来看 [Voxt](https://github.com/sgl-project/sglang-omni/tree/main/Voxt) 会议模式在不同外放音量下的回声消除效果，以及近端被压低了多少。

| 段 | 系统音轨（Mac） | 麦克风音轨（手机） |
|---|---|---|
| 1 | 无声 | 说话 |
| 2 | 说话，音量 75% | 无声 |
| 3 | 说话，音量 30% | 说话 |
| 4 | 说话，音量 50% | 说话 |
| 5 | 说话，音量 75% | 说话 |

- 每条音轨每段播放同一段音频，各段之间只有系统音量不同。
- 第 k 段开头有 k 声哔。
- 两条音轨不使用相同的词，避免转录稿的回声去重把两者混在一起。

## 用法

需要 macOS（用到 `say`、`afconvert`、`osascript`）、Python 3 和 [uv](https://docs.astral.sh/uv/)。

```sh
uv run --no-project --with numpy python -I make_ablation.py   # 生成 ablation/ 下的音频
python3 server.py                                              # 端口默认 8766，可用 PORT 改
```

1. **Mac：** 打开 http://localhost:8766/ ，点"准备"。
2. **手机：** 和 Mac 连同一个 Wi-Fi，用 Safari 打开页面上显示的地址或扫码，点"准备"。
3. **匹配响度：** 在 Mac 页面上点"测我的声音"，读出页面上的句子；再点"测手机"，按提示用侧键调手机音量，直到显示匹配。
4. **测试：** 在 Voxt 里开始会议，然后在 Mac 页面上点"开始测试"。两边会同时开始播放，Mac 的系统音量按段自动切换，结束后恢复原来的音量。

不想用网页的话，可以用 `./ablation.sh` 在 Mac 上播放，听到 "go" 后手动在手机上播放 `ablation/mic.m4a`。
