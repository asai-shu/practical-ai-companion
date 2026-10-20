import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Stream;

/**
 * 過去問のテキストファイルから、英単語の出現回数を数えるツール。
 *
 * 使い方:
 *   java src/WordFrequency.java [入力フォルダ] [出力CSVファイル]
 *
 * 例:
 *   java src/WordFrequency.java data output/nagoya.csv
 *
 * 入力フォルダの中の .txt ファイル（1年分につき1ファイル。例: 2024.txt）をすべて読み込み、
 * 単語ごとに「合計の出現回数」と「何年分のファイルに出てきたか」をCSVに書き出します。
 */
public class WordFrequency {

    // 数えない単語（中学で習う基本語や、the / of のような機能語）。
    // 結果を見て「これは要らない」と思った単語があれば、ここに追加してください。
    static final Set<String> STOP_WORDS = new HashSet<>(Arrays.asList(
        "the", "and", "for", "are", "but", "not", "you", "all", "any", "can", "had", "her", "was",
        "one", "our", "out", "has", "his", "how", "its", "may", "new", "now", "old", "see", "two",
        "way", "who", "did", "get", "got", "let", "say", "she", "too", "use", "him", "own", "yet",
        "also", "been", "both", "each", "even", "from", "have", "here", "into", "just", "like",
        "made", "make", "many", "more", "most", "much", "must", "only", "over", "same", "some",
        "such", "than", "that", "them", "then", "there", "these", "they", "this", "those", "very",
        "were", "what", "when", "where", "which", "while", "will", "with", "would", "your", "about",
        "after", "again", "being", "could", "does", "doing", "down", "during", "every", "first",
        "other", "should", "their", "through", "under", "until", "upon", "well", "because",
        "before", "between", "however", "might", "never", "often", "people", "really", "still",
        "thing", "things", "think", "time", "want", "year", "years", "know", "take", "come",
        "good", "give", "look", "need", "tell", "work", "day", "man", "men", "why", "off",
        "yes", "ago", "back", "able", "once", "less", "least", "ever", "else", "upon", "within",
        "without", "around", "another", "always", "something", "anything", "nothing",
        "everything", "someone", "anyone", "everyone", "himself", "herself", "itself",
        "themselves", "myself", "yourself", "ourselves", "whose", "whom", "though", "although",
        "either", "neither", "whether", "since", "against", "among", "above", "below", "further",
        "last", "long", "great", "little", "own", "part", "put", "said", "says", "seem", "seems",
        "went", "go", "goes", "going", "gone", "did", "done", "having", "kind", "lot", "lots"
    ));

    // 語尾のルールで元の形に戻すと、意味が変わってしまう単語（まとめない単語）。
    // 例: news を new に、evening を even にまとめてはいけない。
    static final Set<String> NO_MERGE = new HashSet<>(Arrays.asList(
        "news", "evening", "morning", "during", "nothing", "something", "anything", "everything",
        "series", "species", "physics", "economics", "politics", "mathematics", "ethics",
        "always", "perhaps", "various", "series", "means", "lens", "bias", "ceiling", "feeling",
        "building", "meaning", "beginning", "spring", "string", "nursing", "clothes", "goods",
        "arms", "manners", "customs", "glasses", "savings", "earnings", "surroundings", "needs"
    ));

    // 英単語を見つけるための正規表現（アルファベットの並び。'の後ろも含める）。
    static final Pattern WORD_PATTERN = Pattern.compile("[a-z]+(?:'[a-z]+)?");

    public static void main(String[] args) throws IOException {
        Path inputDir = Paths.get(args.length >= 1 ? args[0] : "data");
        Path outputFile = Paths.get(args.length >= 2 ? args[1] : "output/word_frequency.csv");

        if (!Files.isDirectory(inputDir)) {
            System.err.println("入力フォルダが見つかりません: " + inputDir.toAbsolutePath());
            System.exit(1);
        }

        List<Path> files = listTextFiles(inputDir);
        if (files.isEmpty()) {
            System.err.println(".txt ファイルがありません: " + inputDir.toAbsolutePath());
            System.exit(1);
        }

        // 単語（見た目の形のまま）ごとの合計回数と、出てきたファイル名
        Map<String, Integer> counts = new HashMap<>();
        Map<String, Set<String>> filesByWord = new HashMap<>();

        for (Path file : files) {
            String fileName = file.getFileName().toString();
            String text = Files.readString(file, StandardCharsets.UTF_8);
            for (String word : extractWords(text)) {
                counts.merge(word, 1, Integer::sum);
                filesByWord.computeIfAbsent(word, k -> new TreeSet<>()).add(fileName);
            }
        }

        // studies / studied / studying などを study にまとめる
        List<Entry> entries = mergeForms(counts, filesByWord);

        // 「出てきた年数」が多い順、同じなら「合計回数」が多い順に並べる
        entries.sort((a, b) -> {
            if (a.files.size() != b.files.size()) {
                return b.files.size() - a.files.size();
            }
            if (a.total != b.total) {
                return b.total - a.total;
            }
            return a.word.compareTo(b.word);
        });

        writeCsv(outputFile, entries, files.size());

        System.out.println(files.size() + " 個のファイルを読み込みました。");
        System.out.println(entries.size() + " 語を " + outputFile + " に書き出しました。");
        System.out.println();
        System.out.println("上位20語:");
        for (int i = 0; i < Math.min(20, entries.size()); i++) {
            Entry e = entries.get(i);
            System.out.printf("%3d. %-15s %4d回 / %d年分%n", i + 1, e.word, e.total, e.files.size());
        }
    }

    /** フォルダの中の .txt ファイルを名前順に集める。 */
    static List<Path> listTextFiles(Path dir) throws IOException {
        try (Stream<Path> stream = Files.list(dir)) {
            return stream
                .filter(p -> p.getFileName().toString().toLowerCase().endsWith(".txt"))
                .sorted()
                .toList();
        }
    }

    /** テキストから、数える対象の単語を取り出す。 */
    static List<String> extractWords(String text) {
        // スキャンした文章では、行の終わりで単語が「envi-」「ronment」のように切れていることがあるので、つなげる
        text = text.replaceAll("-\\s*\\R\\s*", "");
        text = text.toLowerCase();
        // 曲がった引用符 ’ を普通の ' にそろえる
        text = text.replace('’', '\'');

        List<String> words = new ArrayList<>();
        Matcher m = WORD_PATTERN.matcher(text);
        while (m.find()) {
            String word = m.group();
            if (word.endsWith("'s")) {
                word = word.substring(0, word.length() - 2); // Japan's → japan
            }
            if (word.contains("'")) {
                continue; // don't, it'll などの短縮形は基本語なので数えない
            }
            if (word.length() <= 2 || STOP_WORDS.contains(word)) {
                continue;
            }
            words.add(word);
        }
        return words;
    }

    /**
     * 語尾が変化した形を、元の形にまとめる。
     * 誤ってまとめないように、「元の形が同じ過去問の中に実際に出てきた場合だけ」まとめる。
     */
    static List<Entry> mergeForms(Map<String, Integer> counts, Map<String, Set<String>> filesByWord) {
        Map<String, Entry> merged = new TreeMap<>();
        for (String form : counts.keySet()) {
            String base = findBase(form, counts);
            Entry entry = merged.computeIfAbsent(base, Entry::new);
            entry.total += counts.get(form);
            entry.files.addAll(filesByWord.get(form));
            entry.forms.put(form, counts.get(form));
        }
        return new ArrayList<>(merged.values());
    }

    /** 単語の元の形を探す。見つからなければそのまま返す。 */
    static String findBase(String form, Map<String, Integer> counts) {
        String current = form;
        // stopping → stopp → stop のように2段階で戻ることがあるので、数回くり返す
        for (int i = 0; i < 3; i++) {
            String next = oneStepBase(current, counts);
            if (next == null) {
                break;
            }
            current = next;
        }
        return current;
    }

    /** 語尾を1つ外した候補のうち、過去問に出てきたものを返す。なければ null。 */
    static String oneStepBase(String word, Map<String, Integer> counts) {
        if (NO_MERGE.contains(word)) {
            return null;
        }
        List<String> candidates = new ArrayList<>();
        if (word.endsWith("ies")) {
            candidates.add(cut(word, 3) + "y");               // studies → study
        }
        if (word.endsWith("ied")) {
            candidates.add(cut(word, 3) + "y");               // studied → study
        }
        if (word.endsWith("es")) {
            candidates.add(cut(word, 2));                     // watches → watch
        }
        if (word.endsWith("s") && !word.endsWith("ss") && !word.endsWith("us") && !word.endsWith("is")) {
            candidates.add(cut(word, 1));                     // books → book
        }
        if (word.endsWith("ed")) {
            candidates.add(cut(word, 1));                     // used → use
            candidates.add(cut(word, 2));                     // walked → walk
            candidates.add(undouble(cut(word, 2)));           // stopped → stop
        }
        if (word.endsWith("ing")) {
            candidates.add(cut(word, 3));                     // reading → read
            candidates.add(cut(word, 3) + "e");               // making → make
            candidates.add(undouble(cut(word, 3)));           // running → run
        }
        for (String c : candidates) {
            if (c != null && c.length() >= 3 && !c.equals(word) && counts.containsKey(c)) {
                return c;
            }
        }
        return null;
    }

    static String cut(String word, int n) {
        return word.length() > n ? word.substring(0, word.length() - n) : null;
    }

    /** 最後の2文字が同じ子音なら1文字にする（stopp → stop）。 */
    static String undouble(String s) {
        if (s == null || s.length() < 2) {
            return null;
        }
        char last = s.charAt(s.length() - 1);
        char prev = s.charAt(s.length() - 2);
        if (last == prev && "aeiou".indexOf(last) < 0) {
            return s.substring(0, s.length() - 1);
        }
        return null;
    }

    /** 結果をCSVに書き出す（Excelで開いても文字化けしないよう、先頭にBOMを付ける）。 */
    static void writeCsv(Path outputFile, List<Entry> entries, int fileCount) throws IOException {
        if (outputFile.getParent() != null) {
            Files.createDirectories(outputFile.getParent());
        }
        StringBuilder sb = new StringBuilder("﻿");
        sb.append("順位,単語,合計回数,出てきた年数(全").append(fileCount).append("年),出てきたファイル,まとめた形\n");
        for (int i = 0; i < entries.size(); i++) {
            Entry e = entries.get(i);
            List<String> forms = new ArrayList<>();
            for (Map.Entry<String, Integer> f : e.forms.entrySet()) {
                forms.add(f.getKey() + "(" + f.getValue() + ")");
            }
            sb.append(i + 1).append(',')
              .append(e.word).append(',')
              .append(e.total).append(',')
              .append(e.files.size()).append(',')
              .append('"').append(String.join(" ", e.files)).append("\",")
              .append('"').append(String.join(" ", forms)).append("\"\n");
        }
        Files.writeString(outputFile, sb.toString(), StandardCharsets.UTF_8);
    }

    /** まとめた後の1単語分のデータ。 */
    static class Entry {
        final String word;
        int total = 0;
        final Set<String> files = new TreeSet<>();
        final Map<String, Integer> forms = new TreeMap<>();

        Entry(String word) {
            this.word = word;
        }
    }
}
