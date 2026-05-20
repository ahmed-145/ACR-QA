FIGURES DIRECTORY
=================

Place your image files here. Supported formats: .png, .jpg, .pdf, .eps

Required images (referenced in the document):
----------------------------------------------
1. ksiu_logo.png     -- KSIU university logo (for cover page)
                        Uncomment the \includegraphics line in frontmatter/cover.tex
                        and remove the \figplaceholder line when added.

All other figures in the book use \figplaceholder{} commands, which render
as grey placeholder boxes with a description. Replace each one with:

    \includegraphics[width=0.85\textwidth]{your_image_filename}

(omit the file extension — LaTeX will find .png, .jpg, .pdf automatically)

Figure naming convention:
    fig_ch1_pipeline.png
    fig_ch3_architecture.png
    fig_ch3_db_schema.png
    fig_ch3_docker.png
    fig_ch5_owasp.png
    fig_ch5_confidence_dist.png
