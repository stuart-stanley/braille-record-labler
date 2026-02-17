# braille-record-labler

![Picture of collection of records with braille labels](braille_record_labeler/assets/readme_collection.png)

## Intro
Welcome to a tool to create 3d printable braille labels for vinyl records! This came about
when my housemate, who happens to be blind, foolishly got into old style LP records. Super cool
and fun, _but_ 1) using your camera to scan the jacket one by one is painful and the cool
artwork can really confuse it, and 2) we have a labler, but the stickers tend to fall off easily
and when they are shelved together that gets even worse.

So, this project was born! In a nutshell, you create a file containing your list of records and
then one by one, generate a file you can 3D print. There are some extra bits to makes it easier
to keep track of what you have finished printing and such, but that basically that's it!

Note: you will need to do some one-time setup to run this. I have that info at the bottom
in the "setting things up" section.

## Features:

- One line for the artist name, one line for the LP name.
- ability to have "short names" for artist and LP name to deal with braille not fitting on the
  size of label your printer can make.
- Optional "tab" sticking out on the front so you can see the first few chacters of the arist and
  lp name without shoving records aside to reach the whole label.
- Optional visual characters on the "back" side of the tab for the silly sighted person to
  home in on the right part of the alphabet!
- Optional ability to reverse the braille text. There is a fun story behind that in the
  section called "design and history."
- driven by a cli that keeps track of each label, letting you:
  - see if it needs to be printed. Either because it never has or you changed something in the
    configuration that would change what gets printed.
  - see if the print file (.stl) has been created, but not printed yet. 
  - validate if the label(s) can be printed on this printer's bed.
  - generate .scad files, so you can tinker around in openSCAD.
  - "print" the label to a .stl file.
  - mark a given label as having been printed.
  

## Defining records

By default, your shining collection of LPs are placed in a file called "lp_database.yml" in your
current directory. You can override that with the `--lp-database-file` option on the `braille-record-labler` command. There is an example file (the shared list of my housemate's a my collection) in `braille_record_labeler/example_lp_database.yml`

The file has three top level values: the printer, the label format, and the records themselves.
I'll put an example here, and then break them out into three sections with more info.

```
active_printer: 'M200V2'
label_format:
  min_forward_tag_depth__mm: 20
  forward_tag_depth_characters: 2
  forward_tag_do_visual_characters: true
  back_side_depth__mm: 50
  front_side_min_depth__mm: 50
  default_pressure_bump__mm: 3
  braille_back_to_front: False
record_data:
  app_ammonis_avenue:
    full_artist: 'alan parsons project'
    full_lp_name: 'ammonia_avenue'
    thickness__mm: 2
  metric_underground:
    full_artist: 'metric'
    full_lp_name: 'old world underground where are you now'
    short_lp_name: 'old world underground'
```

### active_printer

The `active_printer` is a simple string saying what printer you have. Printers are defined
in `braille_record_labler/default_configish.yml` and basically hold the geometry of the printing space.
Since I currently only have this one tiny Malyan M200 V2, that's what you have available. Open an
issue on github or do a pull request with your printer!

The format is simple:
`active_printer: '<printer-name>'`

E.G:
`active_printer: 'M200V2'`

### label_format:

The `label_format` block lets you define and tune what the label looks like. 


## Printer settings

notes from experiments to turn into suggestions:
- print "on edge" (which is how the stl is generated, so probably just works)
- print with a skirt, especially on long depth prints. They like to detatch and warp upwards
  at the prong end.
- "normal" quality seems to work best just because finer tends to thread more.
- printing one at a time makes for a cleaner print, but that could just because I haven't
  dialed in setting to limit threading.


## Setting things up
