"""混入スキャン(異言語の字形・語彙 / 秘密様文字列 / 内部符丁)= 汎用knowledge 同梱の監査ツール。

読み取り専用の監査コマンド(08 §6-3)。対象を変更しない。

配置と運用(正典 = 01 §13・§14.1):
  原本 = 汎用knowledge リポジトリの `tools/scan_lang.py`(このファイル)。
  **clone 内を直接実行せず、プロジェクトの `knowledge/` 直下へコピーして運用する**(copy-out 型)。
  理由: clone は読み取り専用(01 §11)だが、検出リストは発見の都度育てる必要があるため(07 U14)。
  コピーのヘッダーには**原本の HEAD と版を記録**し、pull のたびに差分を確認する(07 U8)。

実行するのは節目のみ(毎回の更新では実施しない = 01 §14.1):
  ①原本のバージョンアップ(CHANGELOG を書くとき)②knowledge の大部整理・吸収作業
  ③ユーザーの指示

使い方(入力モードは必ず 1 つ以上指定する。未指定・未知のオプションは **エラー終了(rc=2)**):
  # ① リポジトリの追加行(PR のマージ前後のゲート)
  git diff main...HEAD --unified=0 | python3 .scan_lang.py --diff -
  # ② 指定ファイル(複数可)
  python3 .scan_lang.py --no-code --files knowledge/<project>/10_開発ログ.md ...
  # ③ ディレクトリ配下の *.md を再帰走査(節目点検 = 01 §14)
  python3 .scan_lang.py --no-code --root knowledge/<project>
  python3 .scan_lang.py --no-code --root knowledge/generic     # 汎用 clone は監査のみ(編集しない)
  # ④ 自己検証(検出能力の確認 = 「0 件」が空振りでないことの担保)
  python3 .scan_lang.py --self-test

オプション:
  --no-code   符丁(D/F/U + 番号)の検出を省略。**knowledge 内では符丁は合法**(01 §6 例外)なので
              knowledge の走査では必ず付ける。リポジトリ側(コミットメッセージ・PR 本文・追跡文書の
              追加行)では付けない。
  --self-test 合成文字列で検出能力を確認する(合格なら rc=0)。

判定基準(**件数そのものでは判定しない**):
  検出された各件が「正当」か「非正当」かを人が判定する。**非正当 0 件 = 合格**。
  正当の例 = ①knowledge 内の符丁(--no-code 忘れ)②教訓・記録の中で当該字形/語彙を引用している行
  ③このファイル自身の検出リスト。
  **注意**: 検出は列挙型のリストに依存する = **「0 件」は混入が無いことの証明ではない**(07 U14)。
  走査対象・行数は必ず出力で確認する(0 ファイル = 空振り = rc=2 で失敗する)。
  結果の報告には「走査: N ファイル / M 行」を必ず併記する(08 §6-6)。

検出対象:
  1) 符丁: D/F/U + 番号(内部番号の外部持ち出し禁止の規約用 = 01 §6)
  2) PAT様: github_pat_ / ghp_ + 長いトークン文字列(05 §6-4)
  3) 簡体字専用字形(コードポイント明示 = 日本語の常用字と同一字形のものを含まない)
     ※ **リストは固定的・網羅的なものにしない** = 新たに発見した字形・語彙を随時追加する(07 U14)。
  4) 中国語語彙(日本語と字形が一致し語としては中国語のもの = 信息/当前/就绪 等)
  5) ハングル(完成形/互換字母)
  6) 欧州語系の疑い(キリル・Greek 以外のアクセント付き Latin。×÷ とギリシャ文字は正当として除外)

更新方法(最小限):
  字形 = _SIMPLIFIED_CODEPOINTS にコードポイント(小文字16進)を追記 / 語彙 = CN_WORDS に追記。
  追加したら **必ず --self-test と、発見元のファイルに対する --files 走査で検出を確認**する(07 U14)。
  正当な検出が増える場合は削除せず、正当なものとして記録する(誤検出ゼロ方針 = 除外リストは作らない)。
  **プロジェクト側コピーで育てた追加のうち汎用的なものは、原本へ PR で還元する**(01 §12.3・§13)。
"""
import pathlib
import re
import sys

CODE_RE = re.compile(r"\b[DFU]\d{1,2}\b")
PAT_RE = re.compile(r"github_pat_[A-Za-z0-9_]{10,}|ghp_[A-Za-z0-9]{10,}")

# 簡体字専用字形(日本語に存在しない字形のみ = 誤検出ゼロ方針)。コードポイントで固定する
_SIMPLIFIED_CODEPOINTS = (
    "4e1c 8f66 957f 95e8 9a6c 89c1 9875 98ce 98de 8bed 8bf4 8bfb 8ba9 94b1 94c1 "
    "56fe 56e2 5e94 6c14 6c49 7ebf 65e0 65f6 663e 5907 590d 591f 5934 513f "
    "519b 519c 51b2 51b3 51b5 51bb 51c0 51c9 51cf 51e4 51ed 5218 5219 521a 521b "
    "5220 8865 89c2 8bc1 8bbe 8ba1 8ba4 5f55 8bb0 5b9e 73b0 9519 7801 8bdd 8be5 "
    "8be6 8bf7 8be2 8c03 8bd5 8fd0 8fd8 8fd9 8fdb 8fdc 8fde 8fdf 9009 76d1 76d8 "
    "7d27 7ea0 7ea2 7ea6 7ea7 7eaa 7eaf 7eb8 7eb9 7ec6 7ec8 7ec4 7ed3 7ed9 7edc "
    "7edd 7edf 7ee7 7ee9 7eed 7ef4 7eff 7f13 7f16 7f29 7f3a 7f57 7f5a 7f62 804c "
    "8054 806a 8083 80a4 80c0 8111 8138 8230 8270 8282 82cf 8303 8350 8363 836f "
    "83b7 8425 8427 84dd 864f 8651 8680 8845 8bb2 8bba 8bbf 8bc6 8bca 8bd1 8bd7 "
    "8bf8 8bef 8c22 8c31 8d1d 8d1e 8d1f 8d22 8d23 8d25 8d26 8d27 8d28 8d29 8d2a "
    "8d2b 8d2d 8d2e 8d2f 8d31 8d34 8d35 8d37 8d38 8d39 8d3a 8d4b 8d4c 8d4e 8d4f "
    "8d50 8d54 8d5a 8d5b 8d60 8d62 8d75 8d8b 8dc3 8f68 8f69 8f6c 8f6e 8f6f 8f70 "
    "8f7d 8f7f 8f83 8f85 8f86 8f88 8f89 8f91 8f93 8f96 8f97 8fa9 8fbe 8fc1 8fc7 "
    "8fdd 9002 900a 9012 9057 90ae 90bb 90d1 915d 91ca 9489 9488 9493 9499 949f "
    "94a2 94a5 94a9 94c3 94c5 94dc 94fe 9500 9501 9505 950b 9526 952e 953b 9547 "
    "955c 95ea 95ed 95ee 95ef 95f0 95f2 95f4 95f9 95fa 95fb 95e5 9601 9605 9610 "
    "961f 9636 9645 9646 9648 9655 9668 9669 9690 96be 96fe 97e9 9876 9879 987a "
    "987b 9884 987d 987e 987f 9881 9882 9896 9897 9898 989c 989d 98d8 996d 996e "
    "9970 9971 9972 9975 997a 997c 997f 9986 9a61 9a8f 9a91 9a97 9a9a 9a8c 60ca "
    "9ac5 9b13 9f50 9f7f 9f84 9f99 9f9f 6237 518c 73af 52a1 7f51 5e76 53d8 62df "
    "6001 6863 4ef7 542f 8fb9 5904 5e7f 8bae 62a4 62a5 573a 574f 5757 575a 6267 "
    "6269 6270 6548 6743 4e3a 5355 4eec 5bf9 5173 4e49 4e25 4ea7 4e66 4e70 "
    "52a8 4f1e"
)
SIMPLIFIED = {chr(int(cp, 16)) for cp in _SIMPLIFIED_CODEPOINTS.split()}

# 中国語語彙(日中同字形で文字単位では捕まらない語を含む)
CN_WORDS = [
    "文档", "代价", "状态", "当前", "模拟", "缓存", "会话", "变量", "删除", "验证",
    "设计", "实现", "记录", "观察", "处理", "默认", "数据", "时间", "问题", "信息",
    "网络", "服务", "轮询", "并发", "串行", "用户", "账号", "密码", "登录", "注册",
    "错误", "异常", "环境", "就绪",
]
HANGUL_RE = re.compile(r"[\uac00-\ud7af\u1100-\u11ff\u3130-\u318f]")
# ギリシャ文字(α/β 等)は実験腕名・技術記号として正当 = 検出対象から除外
EURO_RE = re.compile(r"[\u0400-\u04ff\u00c0-\u00ff\u0100-\u017f]")
EURO_ALLOW = set("×÷")   # 記号として正当な Latin-1 文字


def scan_line(text: str, where: str, hits: list) -> None:
    for m in CODE_RE.finditer(text):
        hits.append(f"[符丁] {where}: {m.group(0)!r} … {text.strip()[:100]}")
    for m in PAT_RE.finditer(text):
        hits.append(f"[PAT様] {where}: {m.group(0)[:12]}…(masked)")
    for i, ch in enumerate(text):
        if ch in SIMPLIFIED:
            hits.append(f"[簡体字形] {where}: {ch!r}(U+{ord(ch):04X}) … "
                        f"{text.strip()[max(0, i - 30):i + 30]!r}")
    for w in CN_WORDS:
        if w in text:
            hits.append(f"[中国語語彙] {where}: {w!r} … {text.strip()[:100]}")
    for m in HANGUL_RE.finditer(text):
        hits.append(f"[ハングル] {where}: {m.group(0)!r} … {text.strip()[:100]}")
    for m in EURO_RE.finditer(text):
        if m.group(0) not in EURO_ALLOW:
            hits.append(f"[欧州語系] {where}: {m.group(0)!r} … {text.strip()[:100]}")


SKIP_DIRS = {".git", "node_modules", "dist", "var", "__pycache__", ".venv"}


def fail(msg: str) -> "NoReturn":
    """引数・対象の不備 = **rc 2 で失敗**(空振りして『検出 0 件』を返さないための強制 = 07 U14)"""
    print(msg, file=sys.stderr)
    raise SystemExit(2)


def _iter_md(root: str):
    base = pathlib.Path(root)
    if base.is_file():
        yield base
        return
    if not base.is_dir():
        fail(f"[エラー] --root の対象が見つかりません: {root}")
    for path in sorted(base.rglob("*.md")):
        if not any(part in SKIP_DIRS for part in path.parts):
            yield path


def parse(argv: list) -> dict:
    """引数の厳格な解析。**未知のオプション/引数・入力モード無しはエラー終了**(空振りの防止 = 07 U14)"""
    opts = {"no_code": False, "diff": False, "self_test": False, "files": [], "roots": []}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--no-code":
            opts["no_code"] = True
        elif a == "--diff":
            opts["diff"] = True
        elif a == "--self-test":
            opts["self_test"] = True
        elif a == "--files":
            i += 1
            while i < len(argv) and not argv[i].startswith("--"):
                opts["files"].append(argv[i])
                i += 1
            continue
        elif a == "--root":
            i += 1
            if i >= len(argv):
                fail("[エラー] --root の引数(ディレクトリ)が指定されていません")
            opts["roots"].append(argv[i])
        elif a == "-":
            if not opts["diff"]:
                fail("[エラー] `-`(標準入力)は --diff と一緒に使ってください")
            # --diff の stdin マーカー = 無視してよい(入力は sys.stdin から読む)
        else:
            fail(
                f"[エラー] 未知のオプション/引数: {a!r}\n"
                f"  使えるもの = --diff [-] / --files <path...> / --root <dir> / --no-code / --self-test\n"
                f"  (未知の引数を無視すると『走査していないのに検出 0 件』になる = 07 U14)")
        i += 1
    if not (opts["diff"] or opts["files"] or opts["roots"] or opts["self_test"]):
        fail("[エラー] 入力モード(--diff / --files / --root / --self-test)が指定されていません")
    return opts


def self_test() -> int:
    """検出能力の自己検証(合成文字列)。リスト更新後の確認用 = 合格で rc 0"""
    cases = [
        ("材料は就绪", "中国語語彙"),
        ("ログイン自动化", "簡体字形"),
        ("knowledge 伞下に置く", "簡体字形"),
        ("github_pat_ABCDEFGHIJKL", "PAT様"),
        ("F70 の記録", "符丁"),
        ("안녕하세요", "ハングル"),
        ("naïve café", "欧州語系"),
        ("日本語のみの普通の行です。", None),
    ]
    failed = 0
    for text, expect in cases:
        hits: list = []
        scan_line(text, "self-test", hits)
        got = hits[0].split("]")[0][1:] if hits else None
        ok = (got == expect) if expect else (not hits)
        print(f"  {'OK ' if ok else 'NG '} {text!r} → {got or '検出なし'}(期待 = {expect or '検出なし'})")
        failed += 0 if ok else 1
    print(f"自己検証: {len(cases) - failed}/{len(cases)} 合格")
    return 1 if failed else 0


def main(argv: list) -> int:
    opts = parse(argv)
    if opts["no_code"]:
        global CODE_RE
        CODE_RE = re.compile(r"(?!x)x")   # 何にも一致しない(符丁は knowledge 内で合法 = 01 §6 例外)
    if opts["self_test"]:
        return self_test()

    hits: list = []
    n_files = 0
    n_lines = 0
    if opts["diff"]:
        cur = "?"
        for raw in sys.stdin.read().splitlines():
            n_lines += 1
            if raw.startswith("+++ b/"):
                cur = raw[6:]
            elif raw.startswith("+") and not raw.startswith("+++"):
                scan_line(raw[1:], cur, hits)
        n_files = -1   # diff はファイル数を集計しない
    for f in opts["files"]:
        try:
            text = open(f, encoding="utf-8").read()
        except OSError as e:
            hits.append(f"[読めない] {f}: {e}")
            continue
        n_files += 1
        for n, line in enumerate(text.splitlines(), 1):
            n_lines += 1
            scan_line(line, f"{f}:{n}", hits)
    for root in opts["roots"]:
        for path in _iter_md(root):
            try:
                text = path.read_text(encoding="utf-8")
            except OSError as e:
                hits.append(f"[読めない] {path}: {e}")
                continue
            n_files += 1
            for n, line in enumerate(text.splitlines(), 1):
                n_lines += 1
                scan_line(line, f"{path}:{n}", hits)

    scope = "diff(標準入力)" if opts["diff"] else f"{n_files} ファイル / {n_lines:,} 行"
    if n_files == 0 and not opts["diff"]:
        for h in hits:      # 読めなかった理由(パス違い等)を隠さず出す
            print(" " + h, file=sys.stderr)
        fail(f"[エラー] 走査対象が 0 件でした(引数を確認してください): {scope}")
    if hits:
        print(f"走査: {scope} → 検出 {len(hits)} 件(各件が正当かは人が判定する = docstring):")
        for h in hits[:80]:
            print(" ", h)
        if len(hits) > 80:
            print(f"  … ほか {len(hits) - 80} 件")
        return 1
    print(f"走査: {scope} → 検出 0 件(= 未検出。リストは非網羅 = 07 U14)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
