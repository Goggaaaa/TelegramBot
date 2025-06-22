from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.dispatcher import FSMContext
from Database import database as db
from states import Training
import markups as mks
from time import sleep
import os

# Prefixes for callback data
CATEGORY_PREFIX = 'category:'
TRAINING_PREFIX = 'training:'

async def init_trainings(dp, path):

    # Создание стандартных категорий тренировок в виде папок
    try:
        os.makedirs(f'{path}/Training/Trainings/Набор веса', exist_ok=True)
        os.makedirs(f'{path}/Training/Trainings/Похудение', exist_ok=True)
        os.makedirs(f'{path}/Training/Trainings/Удержание веса', exist_ok=True)
    except Exception:
        pass


    # Функция начала тренировок
    async def start_training(training_info, callback_query, state):

        # Состояние активной тренировки
        await Training.active_training.set()

        try:
            # Открытие файла тренировки через путь, который берется из БД
            with open(f'{path}/Training/Trainings/{training_info[0]}/{training_info[1]}/{training_info[2]}.txt', encoding="utf-8") as file:
                lines = file.readlines()

                # Сохранение данных о тренировке в хранилище
                await state.update_data(lines=lines, line_number=0)

            await callback_query.message.answer('Вы готовы начать тренировку?',
                                                reply_markup=mks.start_training_menu)
        except FileNotFoundError:
            await callback_query.message.answer('Вы еще не выбрали тренировку!',
                                                reply_markup=mks.not_chosen_training)


    @dp.callback_query_handler(lambda c: c.data == 'next_exercise', state=Training.active_training)
    async def next_exercise(callback_query: CallbackQuery, state: FSMContext):
        await callback_query.message.delete()

        data = await state.get_data()
        lines = data.get('lines', [])
        line_number = data.get('line_number', 0)

        try:
            line = lines[line_number].split(':')

            exercise_message = await callback_query.message.answer(
                f'Упражнение: <b>{line[0]}</b>\nКоличество подходов: <b>{line[1]}</b>\n\nВидео: <i>{line[2]}</i>',
                parse_mode='HTML',
                reply_markup=mks.active_training_menu)
        except IndexError:
            await callback_query.message.answer('🎉 Поздравляю, тренировка закончена!', reply_markup=mks.to_menu_only)

            current_training_info = db.get_training(callback_query.from_user.id)
            trainings_list = os.listdir(f'{path}/Training/Trainings/{current_training_info[0]}/{current_training_info[1]}')
            day = int(current_training_info[2])

            if day < len(trainings_list):
                new_day = day + 1
            else:
                new_day = 1

            db.set_training(callback_query.from_user.id, current_training_info[0], current_training_info[1], new_day)
            db.update_trainings_count(callback_query.from_user.id)
            return

        try:
            await state.update_data(iteration=3, line=line, exercise_message=exercise_message)
        except Exception:
            pass


    @dp.callback_query_handler(lambda c: c.data == 'next_iteration', state=Training.active_training)
    async def continue_training(callback_query: CallbackQuery, state: FSMContext):

        data = await state.get_data()
        iteration = data.get('iteration', 3)
        line = data.get('line', [])
        exercise_message = data.get('exercise_message')

        try:
            iteration_message = data.get('iteration_message')
            if iteration_message:
                await iteration_message.delete()
        except Exception:
            pass

        if iteration % 2 and iteration < len(line):
            iteration_message = await callback_query.message.answer(f'Количество повторений: {line[iteration]}')
            await state.update_data(iteration_message=iteration_message)
        elif iteration % 2 == 0 and iteration < len(line):
            iteration_message = await callback_query.message.answer(f'⏳ Отдых - {line[iteration]} сек.', reply_markup=mks.active_training_skip_timer_menu)
            await exercise_message.edit_reply_markup(None)

            for seconds in range(int(line[iteration]) - 1, 0, -1):
                if db.check_timer(callback_query.from_user.id) == 0:
                    sleep(1)
                    await iteration_message.edit_text(f'⏳ Отдых - {seconds} сек.', reply_markup=mks.active_training_skip_timer_menu)
                else:
                    db.default_timer(callback_query.from_user.id)
                    break

            await iteration_message.edit_text(f'⌛ Отдых закончен. Приступить к следующему подходу!')
            await exercise_message.edit_reply_markup(mks.active_training_menu)
            await state.update_data(iteration_message=iteration_message)
        else:
            await callback_query.message.answer('❗ Упражнение закончено!\nКак только будешь готов приступить к следующему, нажми на кнопку!', reply_markup=mks.start_training_menu)
            line_number = data.get('line_number', 0) + 1
            await state.update_data(line_number=line_number)
            await exercise_message.delete()

        iteration += 1
        await state.update_data(iteration=iteration)


    @dp.callback_query_handler(lambda c: c.data == 'skip_timer', state='*')
    async def skip_timer(callback_query: CallbackQuery):
        await db.skip_timer(callback_query.from_user.id)


    @dp.callback_query_handler(lambda c: c.data == 'exit_training', state=Training.active_training)
    async def exit_training(callback_query: CallbackQuery, state: FSMContext):
        await callback_query.message.delete()
        data = await state.get_data()

        try:
           iteration_message = data.get('iteration_message', None)
           if iteration_message:
               await iteration_message.delete()
        except Exception:
            pass

        await callback_query.message.answer('Прогресс этой тренировки не сохранится!', reply_markup=mks.training_warning_menu)


    @dp.callback_query_handler(lambda c: c.data == 'continue_training', state='*')
    async def continue_training_handler(callback_query: CallbackQuery, state: FSMContext):
        training_info = db.get_training(callback_query.from_user.id)
        await callback_query.message.delete()
        await start_training(training_info, callback_query, state)


    # Handler for 'new_training' button to show categories
    @dp.callback_query_handler(lambda c: c.data == 'new_training', state='*')
    async def new_training_handler(callback_query: CallbackQuery, state: FSMContext):
        await callback_query.message.delete()
        categories_of_trainings_list = os.listdir(f'{path}/Training/Trainings')
        categories_of_trainings_menu = InlineKeyboardMarkup(row_width=1)
        for category in categories_of_trainings_list:
            category_btn = InlineKeyboardButton(text=category, callback_data=f'{CATEGORY_PREFIX}{category}')
            categories_of_trainings_menu.add(category_btn)
        categories_of_trainings_menu.add(mks.trainings)
        await callback_query.message.answer('Выберите категорию тренировки', reply_markup=categories_of_trainings_menu)


    # Handler for selecting category using callback_data with prefix
    @dp.callback_query_handler(lambda c: c.data and c.data.startswith(CATEGORY_PREFIX), state='*')
    async def category_selected_handler(callback_query: CallbackQuery, state: FSMContext):
        await callback_query.message.delete()
        category = callback_query.data[len(CATEGORY_PREFIX):]
        # Save selected category in state context
        await state.update_data(selected_category=category)

        trainings_list = os.listdir(f'{path}/Training/Trainings/{category}')
        trainings_list_menu = InlineKeyboardMarkup(row_width=1)
        for training in trainings_list:
            training_btn = InlineKeyboardButton(text=training, callback_data=f'{TRAINING_PREFIX}{training}')
            trainings_list_menu.add(training_btn)
        trainings_list_menu.add(mks.trainings)
        await callback_query.message.answer('Выберите тренировку', reply_markup=trainings_list_menu)


    # Handler for selecting training using callback_data with prefix
    @dp.callback_query_handler(lambda c: c.data and c.data.startswith(TRAINING_PREFIX), state='*')
    async def training_selected_handler(callback_query: CallbackQuery, state: FSMContext):
        await callback_query.message.delete()
        training = callback_query.data[len(TRAINING_PREFIX):]
        data = await state.get_data()
        category = data.get('selected_category', None)

        if not category:
            # Category not selected or lost state - ask to reselect
            await callback_query.message.answer('Пожалуйста, сначала выберите категорию тренировки.', reply_markup=mks.trainings)
            return

        # Prepare training info message with exercises summary
        days_list = os.listdir(f'{path}/Training/Trainings/{category}/{training}')
        training_info = ''
        for day in sorted(days_list, key=lambda x: int(x.split('.')[0])):
            training_info += f'\n\n<b>День цикла <u>№{day.split(".")[0]}</u></b>\n\n'
            with open(f'{path}/Training/Trainings/{category}/{training}/{day}', encoding="utf-8") as day_of_training:
                exercises = day_of_training.readlines()
                for exercise in exercises:
                    exercise_info = exercise.split(":")
                    training_info += f'<b>{exercise_info[0]}</b>, количество подходов - {exercise_info[1]}\n'

        # Store selected training and category in state for confirmation
        await state.update_data(selected_training=training, selected_category=category)

        reply_markup = InlineKeyboardMarkup(row_width=2)
        apply_btn = InlineKeyboardButton('✅ Принять', callback_data='apply_training')
        deny_btn = InlineKeyboardButton('↩  Назад', callback_data='new_training')
        reply_markup.insert(apply_btn)
        reply_markup.insert(deny_btn)

        await callback_query.message.answer(f'<b>{training}</b>{training_info}', parse_mode='HTML', reply_markup=reply_markup)


    # Handler for applying the selected training
    @dp.callback_query_handler(lambda c: c.data == 'apply_training', state='*')
    async def apply_training_handler(callback_query: CallbackQuery, state: FSMContext):
        data = await state.get_data()
        category = data.get('selected_category')
        training = data.get('selected_training')

        if not category or not training:
            await callback_query.message.answer('Ошибка выбора тренировки, повторите попытку.', reply_markup=mks.trainings)
            return

        # Save choice in DB, day starts with 1
        db.set_training(callback_query.from_user.id, category, training, '1')

        await callback_query.message.delete()
        await callback_query.message.answer(f'✅ Вы выбрали тренировку - <b>{training}</b>\n', parse_mode='HTML', reply_markup=mks.after_creating_training_menu)


