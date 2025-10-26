import re


class ReviewProcessor:
    def __init__(self):
        self.positive_words = {
            "вкусно",
            "вкусный",
            "вкусная",
            "вкусные",
            "вкусное",
            "отлично",
            "прекрасно",
            "восхитительно",
            "замечательно",
            "рекомендую",
            "советую",
            "супер",
            "класс",
            "шикарно",
            "свежий",
            "свежая",
            "свежее",
            "свежие",
            "качественный",
            "вежливый",
            "внимательный",
            "профессиональный",
            "уютно",
            "комфортно",
            "чисто",
            "быстро",
            "приятно",
            "великолепное",
            "великолепный",
            "великолепная",
            "великолепные",
            "невероятная",
            "невероятный",
        }

        self.negative_words = {
            "плохо",
            "ужасно",
            "отвратительно",
            "кошмар",
            "не советую",
            "разочарован",
            "разочарована",
            "долго",
            "грязно",
            "грубый",
            "дорого",
            "невкусно",
            "испорченный",
            "холодный",
            "горький",
            "пересоленный",
            "медленно",
            "медленный",
        }

        self.negation_words = {
            "не",
            "нет",
            "ни",
            "без",
            "никак",
            "нисколько",
            "отсутствует",
            "невозможно",
            "никакой",
            "ничего",
        }

        self.intensifiers = {
            "очень",
            "крайне",
            "совсем",
            "абсолютно",
            "полностью",
            "совершенно",
            "невероятно",
            "необычайно",
            "чрезвычайно",
            "сильно",
        }

        self.diminishers = {
            "слегка",
            "немного",
            "чуть",
            "чуть-чуть",
            "довольно",
            "вроде",
        }

    def analyze_sentiment_with_negation(self, text):
        """Улучшенный анализ тональности с обработкой отрицаний"""
        words = text.lower().split()
        sentiment_score = 0
        negation_active = False
        intensifier_strength = 1.0

        i = 0
        while i < len(words):
            word = words[i]

            if word in self.negation_words:
                negation_active = True
                i += 1
                continue

            if word in self.intensifiers:
                intensifier_strength = 2.0
                i += 1
                continue

            if word in self.diminishers:
                intensifier_strength = 0.5
                i += 1
                continue

            if word in self.positive_words:
                score = 1.5
                sentiment_score += (
                    score * intensifier_strength * (-1 if negation_active else 1)
                )
                negation_active = False
                intensifier_strength = 1.0

            elif word in self.negative_words:
                score = 1.5
                sentiment_score += (
                    score * intensifier_strength * (1 if negation_active else -1)
                )
                negation_active = False
                intensifier_strength = 1.0

            else:
                if negation_active:
                    negation_active = False

            i += 1

        return sentiment_score

    def detect_negation_patterns(self, text):
        """Детектирует конкретные негативные паттерны"""
        text_lower = text.lower()

        negation_patterns = [
            (r"не\s+\w+но", -2.0),
            (r"не\s+\w+ый", -2.0),
            (r"не\s+\w+ая", -2.0),
            (r"не\s+\w+ое", -2.0),
            (r"не\s+\w+ые", -2.0),
            (r"очень\s+не", -3.0),
            (r"слишком\s+не", -2.5),
            (r"крайне\s+не", -3.0),
        ]

        negation_score = 0
        for pattern, score in negation_patterns:
            if re.search(pattern, text_lower):
                negation_score += score

        return negation_score

    def calculate_sentiment_score(self, text):
        """Комбинированный расчет тональности"""
        base_score = self.analyze_sentiment_with_negation(text)
        negation_score = self.detect_negation_patterns(text)
        text_lower = text.lower()
        strong_positive = any(
            phrase in text_lower
            for phrase in [
                "обязательно вернусь",
                "рекомендую всем",
                "превосходно",
                "восхитительно",
            ]
        )
        strong_negative = any(
            phrase in text_lower
            for phrase in [
                "никому не рекомендую",
                "ужасное",
                "кошмар",
                "отвратительно",
                "больше не пойду",
            ]
        )

        if strong_positive:
            base_score += 3
        if strong_negative:
            base_score -= 3

        return base_score + negation_score

    def extract_verdict(self, text):
        """Извлекает вердикт на основе sentiment score"""
        sentiment_score = self.calculate_sentiment_score(text)

        if sentiment_score >= 4:
            return "Настоятельно рекомендую"
        elif sentiment_score >= 2:
            return "Рекомендую к посещению"
        elif sentiment_score >= 0.5:
            return "Положительное впечатление"
        elif sentiment_score >= -0.5:
            return "Нейтральное впечатление"
        elif sentiment_score >= -2:
            return "Отрицательное впечатление"
        else:
            return "Категорически не рекомендую"

    def extract_meaningful_tags(self, text):
        """Извлекает осмысленные теги по категориям"""
        text_lower = text.lower()
        tags = set()

        self._analyze_food_quality(text_lower, tags)
        self._analyze_service_quality(text_lower, tags)
        self._analyze_atmosphere(text_lower, tags)
        self._analyze_prices_value(text_lower, tags)
        self._analyze_drinks(text_lower, tags)
        self._analyze_restaurant_type(text_lower, tags)

        return sorted(tags)[:8]

    def _analyze_food_quality(self, text_lower, tags):
        """Анализ качества еды"""
        food_indicators = {
            "вкусно": "Вкусная еда",
            "вкусный": "Вкусная еда",
            "вкусная": "Вкусная еда",
            "вкусное": "Вкусная еда",
            "вкусные": "Вкусная еда",
            "свежий": "Свежие продукты",
            "свежая": "Свежие продукты",
            "свежее": "Свежие продукты",
            "свежие": "Свежие продукты",
            "качественный": "Качественные продукты",
            "качественная": "Качественные продукты",
            "качественное": "Качественные продукты",
            "качественные": "Качественные продукты",
            "невкусно": "Невкусная еда",
            "невкусный": "Невкусная еда",
            "испорченный": "Испорченные продукты",
            "испорченная": "Испорченные продукты",
        }

        for indicator, tag in food_indicators.items():
            if indicator in text_lower:
                if tag in ["Вкусная еда", "Свежие продукты", "Качественные продукты"]:
                    negation_found = False
                    for negation_word in ["не", "ни"]:
                        if (
                            f"{negation_word} {indicator}" in text_lower
                            or f"{negation_word}{indicator}" in text_lower
                            or f"{negation_word} очень {indicator}" in text_lower
                            or f"{negation_word} слишком {indicator}" in text_lower
                            or f"{negation_word} совсем {indicator}" in text_lower
                        ):
                            negation_found = True
                            break

                    if not negation_found:
                        tags.add(tag)
                else:
                    tags.add(tag)

    def _analyze_service_quality(self, text_lower, tags):
        """Анализ качества обслуживания"""
        service_indicators = {
            "вежливый": "Вежливый персонал",
            "вежливая": "Вежливый персонал",
            "вежливые": "Вежливый персонал",
            "внимательный": "Внимательный персонал",
            "внимательная": "Внимательный персонал",
            "внимательные": "Внимательный персонал",
            "профессиональный": "Профессиональный персонал",
            "профессиональная": "Профессиональный персонал",
            "профессиональные": "Профессиональный персонал",
            "быстрое обслуживание": "Быстрое обслуживание",
            "быстрая подача": "Быстрое обслуживание",
            "медленное обслуживание": "Медленное обслуживание",
            "долго ждать": "Медленное обслуживание",
            "грубый": "Грубый персонал",
            "грубая": "Грубый персонал",
            "грубые": "Грубый персонал",
        }

        for indicator, tag in service_indicators.items():
            if indicator in text_lower:
                tags.add(tag)

        if ("быстро" in text_lower
            and any(word in text_lower for word in ["обслуживание", "подача", "принесли"])
            and "не быстро" not in text_lower):
            tags.add("Быстрое обслуживание")

        if any(word in text_lower for word in ["долго", "медленно"]) and any(
            word in text_lower for word in ["обслуживание", "подача", "ждать"]
        ):
            tags.add("Медленное обслуживание")

    def _analyze_atmosphere(self, text_lower, tags):
        """Анализ атмосферы и интерьера"""
        atmosphere_indicators = {
            "уютно": "Уютная атмосфера",
            "уютный": "Уютная атмосфера",
            "уютная": "Уютная атмосфера",
            "уютное": "Уютная атмосфера",
            "комфортно": "Комфортная атмосфера",
            "комфортный": "Комфортная атмосфера",
            "комфортная": "Комфортная атмосфера",
            "комфортное": "Комфортная атмосфера",
            "красивый интерьер": "Красивый интерьер",
            "интерьер": "Красивый интерьер",
            "оформление": "Красивый интерьер",
            "дизайн": "Красивый интерьер",
            "атмосфер": "Атмосферное место",
            "романтич": "Романтическая атмосфера",
            "семейн": "Семейная атмосфера",
            "громкая музыка": "Громкая музыка",
            "шумно": "Шумно",
            "тихо": "Тихое место",
            "тесно": "Теснота",
            "мало места": "Теснота",
        }

        for indicator, tag in atmosphere_indicators.items():
            if indicator in text_lower:
                tags.add(tag)

    def _analyze_prices_value(self, text_lower, tags):
        """Анализ цен и соотношения цена/качество"""
        price_indicators = {
            "доступные цены": "Доступные цены",
            "недорого": "Доступные цены",
            "дешево": "Доступные цены",
            "приемлемые цены": "Доступные цены",
            "демократичные цены": "Доступные цены",
            "дорого": "Высокие цены",
            "завышенные цены": "Высокие цены",
            "высокие цены": "Высокие цены",
            "соотношение цена-качество": "Хорошее соотношение цены и качества",
            "цена качество": "Хорошее соотношение цены и качества",
            "стоит своих денег": "Хорошее соотношение цены и качества",
            "переплата": "Завышенные цены",
        }

        for indicator, tag in price_indicators.items():
            if indicator in text_lower:
                tags.add(tag)

        if "цены" in text_lower:
            if any(word in text_lower for word in ["высок", "завышен", "дорог"]):
                if "не дорог" not in text_lower:
                    tags.add("Высокие цены")
            elif any(
                word in text_lower for word in ["доступн", "демократичн", "приемлем"]
            ):
                tags.add("Доступные цены")

    def _analyze_drinks(self, text_lower, tags):
        """Анализ напитков"""
        drinks_indicators = {
            "кофе": "Кофе",
            "чай": "Чай",
            "пиво": "Пиво",
            "вино": "Вино",
            "коктейль": "Коктейли",
            "лимонад": "Лимонады",
            "сок": "Соки",
            "напитки": "Напитки",
            "бар": "Бар",
            "винная карта": "Винная карта",
            "крафтовое пиво": "Крафтовое пиво",
        }

        for indicator, tag in drinks_indicators.items():
            if indicator in text_lower:
                tags.add(tag)

    def _analyze_restaurant_type(self, text_lower, tags):
        """Анализ типа заведения и особенностей"""
        type_indicators = {
            "рекомендую": "Рекомендуют",
            "советую": "Рекомендуют",
            "любимое место": "Любимое место",
            "постоянный клиент": "Постоянные клиенты",
            "вернусь": "Хотят вернуться",
            "очередь": "Популярное место",
            "бронирование": "Бронирование столиков",
            "нет мест": "Популярное место",
            "комплимент": "Комплименты от заведения",
            "подарили": "Комплименты от заведения",
            "завтрак": "Завтраки",
            "бизнес-ланч": "Бизнес-ланч",
            "доставка": "Доставка",
            "веранда": "Летняя веранда",
            "терраса": "Летняя терраса",
        }

        for indicator, tag in type_indicators.items():
            if indicator in text_lower:
                tags.add(tag)

    def process_review(self, text, rating=None):
        """Обрабатывает отзыв и возвращает результат"""
        return {
            "processed_verdict": self.extract_verdict(text),
            "processed_tags": self.extract_meaningful_tags(text),
            "sentiment_score": self.calculate_sentiment_score(text),
            "user_rating": rating,
        }
