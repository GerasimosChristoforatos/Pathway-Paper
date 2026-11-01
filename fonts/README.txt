Inter 4.1 (The Inter Project Authors, https://github.com/rsms/inter), the figure typeface: the static TTF files
Inter-Regular.ttf, Inter-Italic.ttf, Inter-Bold.ttf and Inter-BoldItalic.ttf from the official release archive
Inter-4.1.zip (https://github.com/rsms/inter/releases/download/v4.1/Inter-4.1.zip, folder extras/ttf/;
archive SHA-256 9883fdd4a49d4fb66bd8177ba6625ef9a64aa45899767dde3d36aa425756b11e). Licensed under the SIL Open
Font License 1.1 (OFL-Inter.txt, the LICENSE.txt of the release).

Liberation Sans 2.1 (Red Hat, Inc.; digitized data (c) 2010 Google Corporation), from the Debian package
fonts-liberation (https://github.com/liberationfonts), the fallback typeface (used only if the Inter files are
missing, and for any glyph Inter lacks). Licensed under the SIL Open Font License 1.1 (OFL.txt).

figures/style.py registers these files with matplotlib, so every figure renders identically on any machine.
