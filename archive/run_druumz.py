from archive import druumz

# config = druumz.BasicParameters()

# output_file = r'c:\temp\test_output.xlsx'
# config.from_worksheet(output_file)
# druumz.ConfigFileGenerator(config).write_file(output_file)

input_file = r'c:\temp\class_beats2.xlsx'
druumz.MIDIFileGenerator().do(input_file)
