import re

NUM = r"(?:1[0-7]|[1-9]|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen)"
HARD = re.compile(
    r"(?i)\b(shota\w*|loli|lolis|lolicon|lolita|pedo|pedos|pedophil\w*|paedophil\w*|paedo\w*|"
    r"jailbait|child porn\w*|kiddie porn)\b"
)
AGE = re.compile(
    rf"(?i)\b(?:under-?age|under age|underaged|preteens?|pre-teens?|tweens?)\b|\b{NUM}[- ](?:years?|yrs?|yr)[- ]old\b|\bage(?:d| of)\s+{NUM}\b|\b{NUM}(?:th|st|nd|rd)? birthday\b|\bonly {NUM}\b(?! (?:years|days|hours|minutes|seconds|of|times|more|left|men|people))"
)
YOUNG = re.compile(
    r"(?i)\b(middle school\w*|junior high|elementary|grade school|primary school|kindergarten|preschool|nursery school|"
    r"high ?school\w*|high-school\w*|teen|teens|teenage\w*|schoolgirls?|schoolboys?|school uniform|freshm[ae]n|sophomores?|"
    r"puberty|little girl|little boy|child|children|childlike|kid|kids|minor|minors|genin|academy student\w*|"
    r"first[- ]years?|second[- ]years?|third[- ]years?|(?:6|7|8|9|10|11)th grade|sixth grade|seventh grade|eighth grade|"
    r"ninth grade|tenth grade|eleventh grade|chibi|underaged)\b"
)
SEX_MARK = re.compile(
    r"(?i)\b(lemon|lemons|lemony|lime|smut|smutty|pwp|explicit sex|sex scene|sexual content|nsfw|non-?con|dub-?con|rape)\b|\b(?:rated|rating)\s*:?\s*[\"'(\[]?\s*(?:m|ma|r|nc-?17|x|e|explicit|mature)(?=[\s\"').,\]!:;-]|$)"
)
STRONG_TERM = re.compile(
    r"(?i)\b(cock|cocks|clit|clitoris|cum|cumming|orgasm\w*|penis|vagina|erection|pussy|dildo|blow-?job|hand-?job|"
    r"fellatio|cunnilingus|masturbat\w*|ejaculat\w*|semen|his member|her folds|his length|his shaft|thrust(?:s|ed|ing)? into|"
    r"fuck(?:ed|ing)? (?:her|him|me)|intercourse|had sex|have sex|having sex)\b"
)

MINOR_CAST = re.compile(
    r"(?i)(pok[eé]mon|digimon|madoka|puella magi|k-on|lucky star|azumanga|nichijou|yuru ?yuri|bocchi|card ?captor|"
    r"made in abyss|girls' last tour|spy x family|beyblade|inazuma|yu-?gi-?oh|haikyu|kuroko|prince of tennis|assassination classroom|"
    r"haruhi|toradora|snafu|oregairu|love live|dangan ?ronpa|persona|megami tensei|my hero academia|boku no hero|ouran|shugo chara|"
    r"gakuen alice|tokyo mew mew|pretty cure|precure|doremi|mermaid melody|kodocha|negima|girls und panzer|strike witches|nanoha|"
    r"sailor ?moon|naruto|boruto|bleach|inuyasha|evangelion|code lyoko|mega ?man|sword art|accel world|steins|chaos;head|robotics;notes|"
    r"shingeki|attack on titan|death note|code geass|fullmetal|katekyo|reborn!|kuroshitsuji|black butler|vampire knight|free!|"
    r"hunter x hunter|soul eater|d\.gray|blue exorcist|rosario|high ?school|dxd|love hina|fate|clannad|kanon|little busters|angel beats|"
    r"higurashi|umineko|touhou|vocaloid|kagerou|yu yu hakusho|ranma|eyeshield|slam dunk|yowamushi|ace of diamond|infinite stratos|"
    r"mahouka|date a live|nisekoi|baka and test|gundam|jojo|mob psycho|dragon ball|kill la kill|little witch|my little sister|"
    r"chuunibyou|hyouka|ao haru|kimi ni todoke|aikatsu|idolmaster|kagepro|gakuen|school|academy|magical girl|magi\b|shugo|"
    r"digi|yugioh|summer wars|cardfight|future card|duel masters|medabots|bakugan|zatch|shaman king|hikaru no go|kiddy|"
    r"katawa|corpse party|ib\b|mermaid|ojamajo|captain tsubasa|ghost hunt|fruits basket|maid sama|skip beat|kaichou|tsubasa|"
    r"x/1999|d n angel|dn angel|gravitation|special a|mirai nikki|future diary|another\b|elfen lied|kamisama|noragami|tokyo ghoul|"
    r"song of ice and fire|game of thrones)"
)


def sexual(text):
    if SEX_MARK.search(text[:8000]):
        return True
    return len(STRONG_TERM.findall(text)) >= 3


def verdict(raw, fandom_label, minor_cast):
    if HARD.search(raw):
        return "hard_term"
    if not sexual(raw):
        return None
    if minor_cast or MINOR_CAST.search(fandom_label):
        return "minor_cast_fandom"
    if AGE.search(raw):
        return "age_under_18"
    for m in STRONG_TERM.finditer(raw):
        a = max(0, m.start() - 1000)
        if YOUNG.search(raw[a:m.end() + 1000]):
            return "young_near_sex"
    return None
