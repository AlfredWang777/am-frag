#!/usr/bin/env python3
"""am-frag — 把 `am render` 生成的完整单页 HTML 转成 ZCode Gen UI 内联片段。

用法: am-frag.py <in-page.html> <out-fragment.html> [--mode light|dark|auto] [--theme paper|blueprint|shadcn]

默认 theme=paper（纸张主题与 ZCode 观感最搭）。

做法：去掉 doctype/html/head/body 壳，根属性(data-theme/data-mode/data-style/lang)
搬到根 div#amfrag；CSS 里的 html/body 选择器改指 #amfrag；JS 里的
document.documentElement / document.body 重定向到 #amfrag（宿主沙箱 iframe 内隔离运行）；
fixed 元素（工具栏/回复条/灯箱）改锚到片段根并顶部预留，避免遮挡内容。
"""
import re
import sys


def transform(src, mode=None, theme='paper'):
    style_m = re.search(r'<style[^>]*>(.*?)</style>', src, re.S)
    body_m = re.search(r'<body[^>]*>(.*)</body>', src, re.S)
    html_m = re.search(r'<html([^>]*)>', src)
    if not (style_m and body_m and html_m):
        sys.exit('✗ 输入不像 am 生成的完整页面（缺 style/body/html 标签）')
    css, inner, attrs = style_m.group(1), body_m.group(1), html_m.group(1)

    if mode:
        if 'data-mode' in attrs:
            attrs = re.sub(r'data-mode="[^"]*"', f'data-mode="{mode}"', attrs)
        else:
            attrs += f' data-mode="{mode}"'
    if theme:
        if 'data-theme' in attrs:
            attrs = re.sub(r'data-theme="[^"]*"', f'data-theme="{theme}"', attrs)
        else:
            attrs += f' data-theme="{theme}"'

    css = css.replace('html, body', '#amfrag')
    css = re.sub(r'(?<![\w#.:\[-])html(?=\[)', '#amfrag', css)
    css = re.sub(r'(?<![\w#.:\[-])html(?=:lang)', '#amfrag', css)
    css = re.sub(r'(?<![\w#.:\[-])html\s*(?=\{)', '#amfrag ', css)
    css = re.sub(r'(?<![\w#.:\[-])body(?=[\s,{.:])', '#amfrag', css)
    # 片段模式布局修正：fixed 元素锚到片段根，顶部给工具栏预留空间，避免遮挡内容
    css += ('\n/* am-frag fragment-mode fixes */\n'
            '#amfrag { position: relative; padding-top: 54px; }\n'
            '.am-toolbar { position: absolute; top: 10px; right: 14px; }\n'
            '.am-reply-bar { position: absolute; }\n'
            '.am-lightbox { position: absolute; }\n')

    inner = inner.replace('document.documentElement', "document.getElementById('amfrag')")
    inner = inner.replace('document.body', "document.getElementById('amfrag')")

    frag = (f'<div id="amfrag"{attrs}>\n<style>{css}</style>\n{inner}\n</div>\n')

    leftover = re.findall(r'<(?:!doctype|[>/]?\s*(?:html|head|body))[>\s/]', frag, re.I)
    if leftover:
        sys.exit(f'✗ 输出仍含文档级标签 {leftover[:3]}，转换不完整')
    return frag


def main() -> None:
    argv = list(sys.argv[1:])
    mode = None
    theme = 'paper'
    for flag in ('--mode', '--theme'):
        if flag in argv:
            i = argv.index(flag)
            if i + 1 >= len(argv):
                sys.exit(f'✗ {flag} 需要一个值，例如 {flag} paper')
            if flag == '--mode':
                mode = argv[i + 1]
            else:
                theme = argv[i + 1]
            del argv[i:i + 2]
    if len(argv) != 2:
        sys.exit(__doc__)
    src_path, out_path = argv
    frag = transform(open(src_path, encoding='utf-8').read(), mode, theme)
    open(out_path, 'w', encoding='utf-8').write(frag)
    vh = len(re.findall(r'\d+v[hw]\b', frag))
    fixed = len(re.findall(r'position:\s*fixed', frag))
    notes = []
    if vh:
        notes.append(f'{vh} 处视口单位(vh/vw)在 iframe 里随内容框计算')
    if fixed:
        notes.append(f'{fixed} 处 position:fixed 会钉在 iframe 内框')
    print(f'✓ {out_path} ({len(frag)//1024}KB fragment)' + ('；' + '；'.join(notes) if notes else ''))


if __name__ == '__main__':
    main()
