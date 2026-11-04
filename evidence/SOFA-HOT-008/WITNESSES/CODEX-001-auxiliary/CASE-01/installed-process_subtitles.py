    def process_subtitles(self, video_id, normal_subtitles, automatic_captions):
        """Select the requested subtitles and their format"""
        available_subs, normal_sub_langs = {}, []
        if normal_subtitles and self.params.get('writesubtitles'):
            available_subs.update(normal_subtitles)
            normal_sub_langs = tuple(normal_subtitles.keys())
        if automatic_captions and self.params.get('writeautomaticsub'):
            for lang, cap_info in automatic_captions.items():
                if lang not in available_subs:
                    available_subs[lang] = cap_info

        if not available_subs or (
                not self.params.get('writesubtitles')
                and not self.params.get('writeautomaticsub')):
            return None

        all_sub_langs = tuple(available_subs.keys())
        if self.params.get('allsubtitles', False):
            requested_langs = all_sub_langs
        elif self.params.get('subtitleslangs', False):
            try:
                requested_langs = orderedSet_from_options(
                    self.params.get('subtitleslangs'), {'all': all_sub_langs}, use_regex=True)
            except re.error as e:
                raise ValueError(f'Wrong regex for subtitlelangs: {e.pattern}')
        else:
            requested_langs = LazyList(itertools.chain(
                ['en'] if 'en' in normal_sub_langs else [],
                filter(lambda f: f.startswith('en'), normal_sub_langs),
                ['en'] if 'en' in all_sub_langs else [],
                filter(lambda f: f.startswith('en'), all_sub_langs),
                normal_sub_langs, all_sub_langs,
            ))[:1]
        if requested_langs:
            self.to_screen(f'[info] {video_id}: Downloading subtitles: {", ".join(requested_langs)}')

        formats_query = self.params.get('subtitlesformat', 'best')
        formats_preference = formats_query.split('/') if formats_query else []
        subs = {}
        for lang in requested_langs:
            formats = available_subs.get(lang)
            if formats is None:
                self.report_warning(f'{lang} subtitles not available for {video_id}')
                continue
            for ext in formats_preference:
                if ext == 'best':
                    f = formats[-1]
                    break
                matches = list(filter(lambda f: f['ext'] == ext, formats))
                if matches:
                    f = matches[-1]
                    break
            else:
                f = formats[-1]
                self.report_warning(
                    'No subtitle format found matching "{}" for language {}, '
                    'using {}. Use --list-subs for a list of available subtitles'.format(formats_query, lang, f['ext']))
            subs[lang] = f
        return subs
