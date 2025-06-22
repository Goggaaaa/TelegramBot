from aiogram.types import CallbackQuery, Message
from aiogram.dispatcher import FSMContext
from Database import database as db
from states import Profile
import markups as mks
from time import sleep
import os

async def show_profile(dp, user_id):
    profile_info = list(db.get_profile_info(user_id))

    date_of_registration = f'{profile_info[9].split("-")[2]}.{profile_info[9].split("-")[1]}.{profile_info[9].split("-")[0]}'

    for i in range(1, len(profile_info)):
        if profile_info[i] == None:
            profile_info[i] = ' '
        else:
            if i == 4:
                profile_info[i] += ' см'
            elif i == 3 or i == 6 or i == 7:
                profile_info[i] += ' кг'

    message_for_profile = (f'Имя: {profile_info[0]}\n'
                           f'Пол: {profile_info[1]}\n'
                           f'Возраст: {profile_info[2]}\n'
                           f'Вес: {profile_info[3]}\n'
                           f'Рост: {profile_info[4]}\n'
                           f'Индекс массы тела: {profile_info[5]}\n'
                           f'Масса скелетной мускулатуры: {profile_info[6]}\n'
                           f'Содержание жира: {profile_info[7]}\n'
                           f'Завершенных тренировок: {profile_info[8]}\n'
                           f'Зарегистрирован: {date_of_registration}\n\n\n'
                           f'Для изменения значений воспользуйтесь кнопками ниже 👇')

    await dp.bot.send_message(user_id, message_for_profile, reply_markup=mks.profile_menu)


async def profile(dp, callback):

    await Profile.default.set()

    await show_profile(dp, callback.from_user.id)

    @dp.callback_query_handler(lambda c: c.data == 'add_gender', state='*')
    async def change_gender(callback_query: CallbackQuery, state: FSMContext):

        await state.update_data(position='gender')
        await get_value(dp, callback_query)


    @dp.callback_query_handler(lambda c: c.data == 'add_age', state='*')
    async def change_age(callback_query: CallbackQuery, state: FSMContext):

        await state.update_data(position='age')
        await get_value(dp, callback_query)


    @dp.callback_query_handler(lambda c: c.data == 'add_height', state='*')
    async def change_height(callback_query: CallbackQuery, state: FSMContext):

        await state.update_data(position='height')
        await get_value(dp, callback_query)


    @dp.callback_query_handler(lambda c: c.data == 'add_weight', state='*')
    async def change_weight(callback_query: CallbackQuery, state: FSMContext):

        await state.update_data(position='weight')
        await get_value(dp, callback_query)

    @dp.callback_query_handler(lambda c: c.data == 'add_muscle', state='*')
    async def change_muscle(callback_query: CallbackQuery, state: FSMContext):

        await state.update_data(position='muscle_weight')
        await get_value(dp, callback_query)


    @dp.callback_query_handler(lambda c: c.data == 'add_fat', state='*')
    async def change_fat(callback_query: CallbackQuery, state: FSMContext):

        await state.update_data(position='fat_weight')
        await get_value(dp, callback_query)


async def get_value(dp, callback):

    await Profile.get_value.set()
    await callback.message.delete()

    await callback.message.answer('Введите новое значение:')

    @dp.message_handler(state=Profile.get_value)
    async def get_value_inner(message: Message, state: FSMContext):

        new_value = message.text.strip()

        data = await state.get_data()
        position = data['position']

        # Validation: gender only letters; others only digits
        if position == 'gender':
            if not new_value.isalpha():
                await message.answer('Ошибка: в поле "Пол" можно вводить только буквы. Пожалуйста, введите корректное значение:')
                return
        else:
            if not new_value.isdigit():
                await message.answer('Ошибка: в этом поле можно вводить только цифры. Пожалуйста, введите корректное значение:')
                return

        if db.change_profile(message.from_user.id, new_value, position):
            await message.answer('Значение записано!')

            # Redirect back to profile after value update
            await show_profile(dp, message.from_user.id)

            # Reset state to default
            await Profile.default.set()

