
import os


song_list = ['ohio_2024_12',
             'ohio_state_2024_12'
             
             
             ]

real_song_list = os.listdir('../temp_music')

college_name = 'ohio'
default_underscore = 2
splity = college_name.split('_')
working_path = os.path.join('..', 'temp_music')

for song in real_song_list:
    song_under = song.split('_')
    get_song_file_underscores = (len(song_under))
    get_college_underscores = len(splity) + default_underscore
    print(song)
    if college_name in song and get_song_file_underscores == get_college_underscores:
        final_file_path = os.path.join(working_path, song)
        os.remove(final_file_path)
    else:
        print('fail')



'''
splity = college_name.split('_')
for song in song_list:
    song_under = song.split('_')
    get_song_file_underscores = (len(song_under))
    get_college_underscores = len(splity) + default_underscore
    print(song)
    for college_string in splity:
        print(college_string)
        if college_string not in song:
            print('do not delete')
        else:
            if get_college_underscores == get_song_file_underscores:
                print('remove shit')
            else:
                print('failed')
        
'''
