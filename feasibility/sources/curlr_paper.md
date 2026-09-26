##### Report GitHub Issue

Content selection saved. Describe the issue below:

![](/static/base/1.0.1/images/icons/smileybones-small.svg)
![arXiv logo](/static/base/1.0.1/images/arxiv-logo-primary-light.svg)

# Opening the House: Datasets for Mixed Doubles Curling

###### Abstract

We introduce the most comprehensive publicly available datasets for mixed doubles curling, constructed from eleven top-level tournaments from the CurlIT Results Booklets spanning 53 countries, 1,112 games, and nearly 70,000 recorded shots. While curling analytics has grown in recent years, mixed doubles remains under-served due to limited access to data. Using a combined text-scraping and image-processing pipeline, we extract and standardize detailed game- and shot-level information, including player statistics, hammer possession, Power Play usage, stone coordinates, and post-shot scoring states. We describe the data engineering workflow, highlight challenges in parsing historical records, and derive additional contextual features that enable rigorous strategic analysis. Using these datasets, we present initial insights into shot selection and success rates, scoring distributions, and team efficiencies, illustrating key differences between mixed doubles and traditional 4-player curling. We highlight various ways to analyze this type of data including from a shot-, end-, game- or team-level to display its versatilely. The resulting resources provide a foundation for advanced performance modeling, strategic evaluation, and future research in mixed doubles curling analytics, supporting broader analytical engagement with this rapidly growing discipline.

Keywords: Mixed Doubles, Curling, Sports Analytics, Dataset Construction, Text Scraping, Image Processing, Open Sports Data, Hammer Efficiency, Power Play Strategy

## I Introduction

Over the past few decades, the quantity and quality of data in sports have increased dramatically. Technologies such as GPS sensors worn by players, optical tracking systems capturing player (x,y) coordinates multiple times per second, and biomechanical sensors embedded in equipment or apparel are now standard in many professional sports to assess movement, improve efficiency and consistency, and help prevent fatigue and injury ([Seçkin et al. (2023)](#bib.bib15); [Torres-Ronda et al. (2022)](#bib.bib16)). However, many of these data sources are proprietary and unavailable for public use. In addition, publicly available data, such as play/event data, are typically restricted to major sports (baseball, basketball, football, hockey, soccer) that have the financial and infrastructural investments to collect them. Where such detailed event or tracking data are not accessible, researchers often must make do with coarse, game-level summaries.

Several researchers have worked to expand the availability of sports analytics data. For example, [Thomas and Ventura (2014)](#bib.bib14) compiled play-level data, shift charts, and shot locations in the National Hockey League (NHL), making these data available through the R package nhlscrapR. In American football, [Yurko et al. (2018)](#bib.bib13) developed nflscrapR, an R package that provides play-level data by parsing the National Football League’s official API. Beyond major sports, [Zhang et al. (2024)](#bib.bib12)
constructed a billiards dataset using the free software Kinovea to collect the frames, turns and strikes from video footage. They then used the data to perform prediction, generate layouts and determine similar billiards layouts. In contrast, 4-player curling in general, and mixed doubles even more so, has received little investment in data infrastructure, limiting the scope of independent analytics in the sport.

Curling analytics as a whole remains in its infancy, with much of the existing research relying on game-level summaries to evaluate team ability and the strategic value of having the hammer. In a recent review, [Zacharias et al. (2024)](#bib.bib6) identified 38 articles focusing on curling strategy and tactics, but none addressing the mixed doubles format within their scope. Mixed doubles curling, often played in international competitions where tournaments rotate across countries and venues, presents unique logistical challenges for data collection. The temporary nature of venues complicates the installation of camera-based tracking systems, while GPS tracking of stones would require substantial investment and buy-in at the highest levels of the sport—resources typically unavailable outside elite tournaments.

Following the lead of prior work in other sports, we recognize the need for a publicly available mixed doubles curling dataset. Such data would enable researchers to investigate novel questions, foster independent analytics, and potentially provide a competitive edge within the sport.

In this paper, we describe the construction of a mixed doubles curling dataset at both the game and shot level and discuss the potential use cases. Starting from CurlIT’s PDF tournament booklets, we extract tournament and game information, linescores, player and team statistics, and rock positions after each shot. We detail the text scraping, image processing, and post-processing methods used to clean the data and generate additional features. The resulting dataset spans 53 countries, 1,112 games, and 11 top level mixed doubles tournaments held between 2016 and 2025. The game-level dataset consists of one row per game and 167 variables describing the game-, team- and player-level statistics. The shot-level dataset contains 66,632 rows and 103 variables detailing the stone placements, the score and the number of stones in various zones of the play area following each shot.

The remainder of the paper is organized as follows. Section [II](#S2 "II 4-Player Curling vs. Mixed Doubles ‣ Opening the House: Datasets for Mixed Doubles Curling") reviews mixed doubles curling, highlighting its similarities and differences relative to standard curling. Section [III](#S3 "III Data collection ‣ Opening the House: Datasets for Mixed Doubles Curling") outlines the data collection and feature engineering process. Section [IV](#S4 "IV Results and Insights from the Mixed Doubles Curling Dataset ‣ Opening the House: Datasets for Mixed Doubles Curling") presents elementary summaries intended to contrast the sports differences from standard curling and serve as a foundation for future research. Section [V](#S5 "V Summary of Contributions ‣ Opening the House: Datasets for Mixed Doubles Curling") concludes with directions for future research utilizing these datasets.

## II 4-Player Curling vs. Mixed Doubles

Curling is a winter sport played on a sheet of ice approximately 150 feet (45.72 meters) long, in which teams slide heavy granite stones, or “rocks,” toward a target. The target, known as the “house,” consists of three concentric rings referred to by their diameters as the “12-ft”, “8-ft”, and “4-ft” circles, shown in Figure [1](#S2.F1 "Fig. 1 ‣ II 4-Player Curling vs. Mixed Doubles ‣ Opening the House: Datasets for Mixed Doubles Curling") as red, white, and blue rings, respectively. A house is located at each end of the sheet. At the center of the house lies the “button,” a small white circle, whose exact center is known as the “pin”; a small hole drilled into the ice to allow precise distance measurements using a special device. Other key markings include
the “center line,” which runs lengthwise through the sheet; the “tee line,” which runs across the sheet through the center of the house; and the “hog line,” the bold red line marking the start of the playing area which ends at the “back line” labeled in Figure [1](#S2.F1 "Fig. 1 ‣ II 4-Player Curling vs. Mixed Doubles ‣ Opening the House: Datasets for Mixed Doubles Curling").

![Refer to caption](2512.16574v2/Manuscript_images/image1.png)

A player attempts a shot by pushing from the “hack,” a foothold behind the house, and sliding a rock toward the opposite house while imparting rotation before release. This rotation causes the stone to follow a curved trajectory, or “curl”, which gives the sport its name.

A game consists of 8–10 intervals of play, called “ends,” in which two teams alternate throwing their rocks. Teams score when one of their rocks is in the house and closer to the pin than any of the opponent’s stones, earning one point for each stone in such a position. Accordingly, teams aim to place their rocks centrally in the house while displacing opposing stones. “Guard” rocks, stones positioned outside the house but within the playing area also known as the “Guard Zone” (displayed in pale blue in Figure [1](#S2.F1 "Fig. 1 ‣ II 4-Player Curling vs. Mixed Doubles ‣ Opening the House: Datasets for Mixed Doubles Curling")), are often used to protect scoring stones from removal. The team with the final rock in an end is said to have the “hammer,” while the opposing team has the “first stone” possession. The hammer is a strategic advantage, as the final shot frequently determines scoring. If the team with the hammer scores, they forfeit the hammer in the next end. If the opposing team scores instead, which is known as a “steal,” the hammer is retained. When no points are scored, the end is said to be “blanked.”

Traditional curling is played between two teams of four players, each delivering two stones per end across the 8–10 ends, depending on the competition level. Standard curling has been a permanent part of the Olympic program since 1998 ([International Olympic Committee, n.d.](#bib.bib4)). A newer variant, “mixed doubles curling,” has grown rapidly in popularity since its introduction at the World Mixed Doubles Curling Championships in 2008 ([The Curling News, 2006](#bib.bib1)) and its inclusion in the Olympics in 2018 ([Vieira, 2022](#bib.bib3)). Mixed doubles retains many of traditional curling’s fundamental mechanics, but key rule changes distinguish it from the 4-player format.

In mixed doubles, each team consists of two players, one male and one female, with games played over eight ends. Each team has six stones per end, one of which is prepositioned before play begins. The prepositioned stones are labeled as position A which is placed as a center guard and position B at the back of the 4-ft ring as shown in left image of Figure [2](#S2.F2 "Fig. 2 ‣ II 4-Player Curling vs. Mixed Doubles ‣ Opening the House: Datasets for Mixed Doubles Curling") by the red and yellow stones, respectively. The team whose stone is in position A delivers the first shot of the end and the team with position B delivers second and therefore has the hammer possession in the end. The team with position A can place their stone either in front or behind the game’s black “guard dot”. The specific guard dot used in a game is determined before the game based on the ice conditions and will remain the same for the entirety of the game. Of the remaining five stones, one player delivers stones 1 and 5, while the other delivers stones 2, 3, and 4.

![Refer to caption](2512.16574v2/Manuscript_images/image2a.png)
![Refer to caption](2512.16574v2/Manuscript_images/image2b.png)

Several rule modifications alter game dynamics relative to standard curling. In 4-player curling, the Free Guard Rule stipulates that until the sixth stone of an end, a guard removed from play may be restored at the opponent’s discretion ([World Curling Federation, 2024](#bib.bib5)). In mixed doubles, the rule is stricter: until the fourth thrown stone of an end, no rock may be removed from play, regardless of type (guard, in-house, prepositioned, or otherwise). If a removal occurs, all stones are reset by the non-offending team to their prior positions automatically, with no option for the opponent to accept the outcome. This increases the number of stones in play and raises the strategic importance of early shot placements.

Blanked ends are also treated differently. In standard curling, the hammer is retained if no points are scored, making blanking an important strategic option when teams prefer to preserve hammer advantage. In mixed doubles, however, a blanked end results in a change of control as to where the prepositioned stones are placed in the next end. The team that takes stone position B, as in Figure [2](#S2.F2 "Fig. 2 ‣ II 4-Player Curling vs. Mixed Doubles ‣ Opening the House: Datasets for Mixed Doubles Curling"), gets the hammer. In nearly all cases, position B is selected and the hammer is taken. Consequently, blanking is both more difficult (given the number of stones in play) and not strategically advantageous. This change eliminates one of the central tactics in 4-player curling strategy, that has been investigated by several authors including [Willoughby and Kostuk (2005)](#bib.bib8) and [Clement (2012)](#bib.bib9).

Another unique feature of mixed doubles is the Power Play. Once per game (excluding extra ends), the team with the decision on the prepositioned stones may call a Power Play at the start of an end. This shifts the prepositioned stones laterally: the hammer stone is placed intersecting the 8-ft and 12-ft rings just above the T-line, while the opposing guard is moved to the same side at a slight angle (Figure [2](#S2.F2 "Fig. 2 ‣ II 4-Player Curling vs. Mixed Doubles ‣ Opening the House: Datasets for Mixed Doubles Curling"), right). This configuration is intended to increase scoring potential by opening access to the button and reducing the likelihood of a steal. Teams may use the Power Play offensively, to attempt a large scoring end, or defensively, to minimize risk of giving up a steal.

While 4-player curling and mixed doubles share the same basic objectives and physical skills—such as sweeping, stone delivery, and shot placement—their strategic landscapes diverge considerably due to these rule changes. However, to date no research has examined whether strategies from traditional curling translate to mixed doubles. By making mixed doubles curling data publicly available, researchers can begin to study these differences systematically, gaining insight into how teams may need to adapt tactics for this distinct variant of the sport.

## III Data collection

Traditional curling analytics draws upon data recorded at varying levels of detail. The most common and accessible are game-level summaries, or linescores (shown in Figure [3](#S3.F3 "Fig. 3 ‣ III Data collection ‣ Opening the House: Datasets for Mixed Doubles Curling")), which track hammer possession and end-level results. These provide a progression of the game comparable to inning-by-inning summaries in baseball. Linescore data are widely available through sources such as the Curling Canada Archive and World Curling, and have been frequently used in prior research due to their simplicity and public accessibility.

![Refer to caption](2512.16574v2/Manuscript_images/image3.png)

At a finer granularity, shot-level data record each delivered stone, along with contextual information and outcomes. CurlingZone, for instance, offers manually tracked shot by shot data for select events, though these resources are proprietary and not openly available. At the most detailed level, real-time performance tracking systems have been developed. [Masui et al. (2015)](#bib.bib7) introduced iCE (intelligent Curling Elicitator), a database platform that enables teams to log detailed shot information and player performance metrics for post-game review. While valuable for coaching and internal team analysis, these systems are likewise not publicly accessible.

Overall, access to curling data remains fragmented. Publicly available sources are generally limited to coarse, game-level summaries, whereas more detailed shot-level and performance data are proprietary. This restricted access has constrained the development of curling analytics and limited the scope of independent research—particularly in the context of mixed doubles.

An important exception are the CurlIT Results Books, which provide the most consistent and detailed publicly available curling data. Published for major competitions, these PDF booklets contain records dating back to 1924 for 4-player curling and 2013 for mixed doubles. Each Results Book includes team and player information, tournament schedules, standings, and game linescores. Beyond game outcomes, they report shot success percentages for both the game and tournament thus far, with breakdowns by shot type (draw, take-out, total) and by turn (clockwise, counter-clockwise, total). Most notably, the Results Books include graphical snapshots of the playing area after every shot, annotated with the shooting country, player, shot type, turn, and shot success percentage (Figure [4](#S3.F4 "Fig. 4 ‣ III Data collection ‣ Opening the House: Datasets for Mixed Doubles Curling")). These detailed records make the CurlIT Results Books the most comprehensive open resource for mixed doubles curling analytics.

![Refer to caption](2512.16574v2/Manuscript_images/image4.png)

To form our dataset, we focus on data from two types of tournaments: the World Mixed Doubles Curling Championships (WMDCC) from 2016 to 2025 (excluding 2020) and the Olympic Winter Games (OWG) in 2018 and 2022. These tournaments were selected because the CurlIT Results Books follow a consistent reporting format across years, and we believe the level of competition is relatively comparable.

Data collection was conducted in four stages using both Python and R. The primary step involved text scraping the CurlIT Results Books to extract structured data on teams, players, games, shots, and standings. Next, we retrieved and processed all shot by shot images included in the Results Books. Image processing was used to identify stone positions, stone colours, and the shooter’s stone for each shot. The extracted data then underwent cleaning and validation to ensure completeness and consistency. Country and player names were standardized across tournaments, and missing information (e.g., absent shot images, unidentified shooters, or unspecified shot types) was corrected wherever possible. Finally, a post-processing stage derived additional features critical to mixed doubles curling analysis. These include hammer possession for each end, identification of Power Play usage (end and team), and whether Power Plays remained available. Using standard curling terminology, we also classified stone positions into defined zones based on their final resting locations, enabling systematic analysis of shot outcomes.

### III-A Text Scraping

Text scraping was used to convert the unstructured tournament records in the CurlIT Results Books into structured data suitable for analysis. The process involved systematically scanning page content, identifying patterns (e.g., keywords, abbreviations, and formatting conventions), and extracting relevant entities such as teams, players, standings, and shot outcomes. Country codes and player names posed the greatest challenges for automated parsing due to occasional formatting irregularities, while numerical fields such as scores, standings, and shot success percentages were generally extracted with minimal intervention.

Not all pages from the Results Books were scraped; instead, we focused on those providing unique and essential information. Specifically:

Title Page, Medalists, and Final Standings: Tournament metadata (location, dates), medal results, and final rankings.

Game Results: Linescores, Last Stone Draw outcomes, timeouts, time remaining, and Power Play usage. In addition, player- and team-level shooting percentages for the game as well as the tournament thus far are provided along with shot success analysis providing a detailed breakdown of these percentages by stone rotation and grouped by draw or take-out and a combined total,

Shot Results: When provided, pages include detailed records of each shot, including shooter, shot type, rotation, and execution rating.

While most tournaments follow consistent formatting, occasional discrepancies—such as missing data, ambiguous player identifiers, or format shifts—required manual corrections to maintain comparability across years. Detailed descriptions of these interventions are provided in the Supplementary Material (Section [VI-A](#S6.SS1 "VI-A Text Scraping Corrections ‣ VI Supplementary Material ‣ Opening the House: Datasets for Mixed Doubles Curling")).

### III-B Image Extraction

Shot by shot images were extracted from the CurlIT Results Books using the fitz package from PyMuPDF in Python. For each shot by shot page, we identified all embedded images with approximate dimensions of 300 × 600 pixels and saved them as shot images. The standard layout, as seen in Figure [4](#S3.F4 "Fig. 4 ‣ III Data collection ‣ Opening the House: Datasets for Mixed Doubles Curling"), consists of one image showing the prepositioned stones, followed by sequential images of shots 1–4 on the first row and shots 5–10 on the second row.

While this procedure was largely automated, several exceptions required manual intervention. For example, the 2016 WMDCC did not include prepositioned stone images. To address this, we manually reconstructed these images by examining the first shot of each end and cross-referencing stone placement, colours, and sheet orientation with the 2017 tournament format. In later tournaments, occasional discrepancies occurred, most commonly when the prepositioned stones image was mistakenly duplicated from the first shot image. In such cases, the incorrect images were replaced with corrected versions sourced from other ends or games with the appropriate configuration.

A complete list of manual corrections, excluding those applied to the 2016 WMDCC, is provided in Supplementary Material (Section [VI-B](#S6.SS2 "VI-B Image Extraction Corrections ‣ VI Supplementary Material ‣ Opening the House: Datasets for Mixed Doubles Curling"), Table [III](#S6.T3 "TABLE III ‣ VI-B Image Extraction Corrections ‣ VI Supplementary Material ‣ Opening the House: Datasets for Mixed Doubles Curling")).

### III-C Image Processing

The shot by shot images extracted from the Results Books required additional processing to standardize orientation, identify stone positions, classify stone colours, and detect the shooter. This step was essential to convert static visual records into structured data suitable for quantitative analysis. The overall workflow was designed to ensure that each shot image could be consistently compared across games, ends, and tournaments despite minor formatting differences between years.

The processing pipeline proceeded as follows:

Orientation: Images were standardized by flipping when necessary so the house always appeared in a consistent position.

Stone Detection: Stones were identified using circle-detection methods, with unused stones in the lower corners masked out.

Colour Classification: Stones were classified as red or yellow based on pixel counts, with shooter colour alternating with each shot.

Shooter Identification: The shooter was identified using tournament-specific markings (a black border in earlier years; a central black dot in later years).

Sequence Validation: When image extraction order was inconsistent, stone coordinates were checked and corrected to restore chronological order.

Figure [5](#S3.F5 "Fig. 5 ‣ III-C Image Processing ‣ III Data collection ‣ Opening the House: Datasets for Mixed Doubles Curling") illustrates the processed images from Figure [4](#S3.F4 "Fig. 4 ‣ III Data collection ‣ Opening the House: Datasets for Mixed Doubles Curling") of the 7t​h7^{th} end in the 2025 WMDCC game between Scotland (red stones) and Italy (yellow stones). Comparing to the original images, the processed images are rotated, lower corners whited out (to avoid detecting unused stones), stones are detected (bright green circles), stone colours are identified, the shooter is highlighted (blue circle), and precise stone coordinates are marked (orange dots).

![Refer to caption](2512.16574v2/Manuscript_images/image5.png)

### III-D Post-Processing

After extracting and processing the shot images, we conducted a post-processing step in R and Python to create comprehensive datasets describing both game- and shot-level details. This stage involved additional cleaning, feature creation, and the integration of contextual game information needed for subsequent analysis.

The main post-processing workflow included:

Cleaning and Standardization

Tournament standings were standardized by converting medal labels (Gold, Silver, Bronze) into numerical ranks (1, 2, 3) to align with the remaining rankings.

Thrower names were cross-checked with the official Entry List to ensure each shot was correctly assigned to the shooting country, labeled as the variable “Rock Country” in Figure [8](#S4.F8 "Fig. 8 ‣ IV Results and Insights from the Mixed Doubles Curling Dataset ‣ Opening the House: Datasets for Mixed Doubles Curling").

Hammer and Power Play Features

The country delivering the second shot of each end was identified as having the hammer and given the variable name “Hammer End” in Figure [8](#S4.F8 "Fig. 8 ‣ IV Results and Insights from the Mixed Doubles Curling Dataset ‣ Opening the House: Datasets for Mixed Doubles Curling").

Power Plays were validated by checking that the average X-coordinate of prepositioned stones was offset from center ice. From this, we determined whether the Power Play was set to the left or right side of the sheet.

New variables were added to indicate Power Play availability at the start of each end, ensuring consistency with hammer rules.

Hammer possession in the first end was used to confirm the Last Stone First End (LSFE) winner, as listed in the game results.

Team Stone Colour Assignment

By comparing the first and second shot colours with hammer possession, we determined each team’s stone colours for the game.

Stone Zone Classification

Moving back to Python, stones were categorized into zones based on their final resting location (Figure [6](#S3.F6 "Fig. 6 ‣ III-D Post-Processing ‣ III Data collection ‣ Opening the House: Datasets for Mixed Doubles Curling")). Zones ranged from weight based (W1 for high guards to W11 for beyond play area) to house rings (Button, “4-ft”, “8-ft”, “12-ft”). The red stone in the “8-ft” ring of Figure [6](#S3.F6 "Fig. 6 ‣ III-D Post-Processing ‣ III Data collection ‣ Opening the House: Datasets for Mixed Doubles Curling") would get a value of 1 for both the “RedW6” and “Red8FT” columns and the score after the shot would be “Red\_Score” is 3 and “Yellow\_Score” is 0.

Stones in front the house were further classified as left (GL), center (GC), or right (GR) guards.

After each shot, scoring was computed by finding the stone closest to the button and counting all stones of the same colour in the house and closer than the nearest opponent stone.

![Refer to caption](2512.16574v2/Manuscript_images/image6.png)

The final datasets included both game- and shot-specific tables, with column descriptions provided in the Supplementary Material (Section [VI-C](#S6.SS3 "VI-C Supplementary Material: Column Definitions ‣ VI Supplementary Material ‣ Opening the House: Datasets for Mixed Doubles Curling")). For compactness, we use {} notation to describe similar columns. For example, the column T{1,2}{F,M}{Draws,TO,TotalGame}{Clock,Counter}Num encodes team (1 or 2), gender (female or male), shot type (draws, take-outs (TO), or game totals), and rotation (clockwise or counter-clockwise). A specific selection such as T1FTOCounterNum would represent the number of counter-clockwise take-outs attempted by the female player on Team 1 during the full match.

Table [I](#S3.T1 "TABLE I ‣ III-D Post-Processing ‣ III Data collection ‣ Opening the House: Datasets for Mixed Doubles Curling") provides a summary of the mixed doubles curling datasets. The game-level dataset includes 1,112 games played by 274 players from 53 countries. The shot-level dataset includes 804 games as not all games include shot by shot details. This dataset includes data from 40 teams, 207 players and results in over 60,000 recorded shots. It also captures detailed end-play structures, including 4,683 regular ends, 1,352 Power Play ends, and 61 overtime ends. This breadth and depth of data enables robust statistical analyses of player behavior, team strategies, and shot success across a diverse international field.

| Dataset | Years | Countries | Players | Games | Reg Ends | PP Ends | OT Ends | Shots |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Games | 2016-2025 (excl. 2020) | 53 | 274 | 1,112 | - | - | - | - |
| Shots | 2016-2025 (excl. 2020) | 40 | 207 | 804 | 4,683 | 1352 | 61 | 60,536 |

### III-E Accessing the Data

The datasets described in this section are publicly available in the CurlR repository. The data can be accessed though GitHub at CurlR by using the commands found in Listing [1](#LST1 "Listing 1 ‣ III-E Accessing the Data ‣ III Data collection ‣ Opening the House: Datasets for Mixed Doubles Curling"). This repository provides comprehensive data tables and accompanying documentation to facilitate reproducible research and further analysis in the field of sports analytics.

## IV Results and Insights from the Mixed Doubles Curling Dataset

The curated datasets provide a rich foundation for quantitative analysis of mixed doubles curling, comprising 268 detailed columns across game- and shot-level data. Figures [7](#S4.F7 "Fig. 7 ‣ IV Results and Insights from the Mixed Doubles Curling Dataset ‣ Opening the House: Datasets for Mixed Doubles Curling") and [8](#S4.F8 "Fig. 8 ‣ IV Results and Insights from the Mixed Doubles Curling Dataset ‣ Opening the House: Datasets for Mixed Doubles Curling") present representative samples from the game and shot datasets, respectively. Shot number 0 denotes the prepositioned stones. With detailed shot- and game-level datasets, the data enable multifaceted analyses of game strategy and performance, allowing for extensions to analyze ends and teams.

![Refer to caption](2512.16574v2/Manuscript_images/image7.png)
![Refer to caption](2512.16574v2/Manuscript_images/image8.png)

### IV-A Shot-Level Analysis

Each shot is graded on a discrete scale—0, 25, 50, 75, or 100—by trained personnel capturing data live during events. These shot grades reflect execution success relative to the intended outcome. However, some subjectivity or uncertainty is inherent, as players may not always explicitly announce their shot intentions or may adapt mid-execution. Comparing mixed doubles success proportions to the World Men’s Curling Championships (WMCC2019, WMCC2021, WMCC2022, WMCC2023, WMCC2024) in Figure [9](#S4.F9 "Fig. 9 ‣ IV-A Shot-Level Analysis ‣ IV Results and Insights from the Mixed Doubles Curling Dataset ‣ Opening the House: Datasets for Mixed Doubles Curling"), front, clearing, and guard shots have the highest average success percentages in mixed doubles. The fraction of 100% scores received in the men’s game (right panel) are higher across all shot types with the largest difference appearing in take-outs. Overall, the most successful shots are those that typically have less risk.

Looking at the proportion of throws attempted in Figure [10](#S4.F10 "Fig. 10 ‣ IV-A Shot-Level Analysis ‣ IV Results and Insights from the Mixed Doubles Curling Dataset ‣ Opening the House: Datasets for Mixed Doubles Curling"), draws dominate the plot for both the mixed doubles and men’s games. For the men, take-outs, hit-and-rolls, clearing and fronts have much larger shares of the action. The types of throws attempted in the two versions of curling are drastically different further enforcing that any analytics should take these aspects into consideration.

### IV-B End-Level Analysis

The scoring behavior in mixed doubles curling differs significantly from traditional 4-player curling. While standard curling scoring distributions are approximately symmetric and centered around scoring 1 point with the hammer (figures available in [Brenzel et al. (2019)](#bib.bib10)), mixed doubles has a gap in the distribution because scoring zero is both difficult and not usually beneficial to the team with hammer. This leads to a fundamentally different scoring distribution in the two variations of the sport.

As illustrated in Figure [11](#S4.F11 "Fig. 11 ‣ IV-B End-Level Analysis ‣ IV Results and Insights from the Mixed Doubles Curling Dataset ‣ Opening the House: Datasets for Mixed Doubles Curling"), the distribution of points scored across ends is relatively consistent, with a notable shift in the 9th end, when there is a much higher frequency of scoring one point with hammer, because that is all they need to win. When it comes to scoring more than one point, end 7 has the highest frequency out of all ends. This may be attributed to strategic use of the Power Play, typically deployed in later ends (5–8). Figure [12](#S4.F12 "Fig. 12 ‣ IV-B End-Level Analysis ‣ IV Results and Insights from the Mixed Doubles Curling Dataset ‣ Opening the House: Datasets for Mixed Doubles Curling") further dis-aggregates scoring outcomes based on Power Play status:

PP Available & Used,

PP Available & Not Used, and

PP Unavailable.

![Refer to caption](2512.16574v2/Manuscript_images/image11.png)
![Refer to caption](2512.16574v2/Manuscript_images/image12.png)

Teams using the Power Play tend to increase their likelihood of scoring 2 or 3 points while reducing the chances of conceding a steal. When the Power Play is unavailable, the likelihood of conceding a single point rises. This effect may be influenced by weaker teams using their Power Play earlier because they are trailing, or by leading teams being more willing to concede a point late in the game. Figures [16](#S6.F16 "Fig. 16 ‣ VI-D Supplementary Material: Scoring Distributions ‣ VI Supplementary Material ‣ Opening the House: Datasets for Mixed Doubles Curling") and [17](#S6.F17 "Fig. 17 ‣ VI-D Supplementary Material: Scoring Distributions ‣ VI Supplementary Material ‣ Opening the House: Datasets for Mixed Doubles Curling") in the Supplementary Material (Section [VI-D](#S6.SS4 "VI-D Supplementary Material: Scoring Distributions ‣ VI Supplementary Material ‣ Opening the House: Datasets for Mixed Doubles Curling")) extend this analysis by overlaying Power Play availability with end number and score differential, providing a multi-dimensional view of scoring tendencies.

### IV-C Game-Level Analysis

The game-level dataset contains high-level summaries of performance for each team across all ends, capturing aggregate statistics such as draw, take-out and total success percentages. These features allow for longitudinal team performance evaluation and broader tournament-level insights.

Figure [13](#S4.F13 "Fig. 13 ‣ IV-C Game-Level Analysis ‣ IV Results and Insights from the Mixed Doubles Curling Dataset ‣ Opening the House: Datasets for Mixed Doubles Curling") visualizes the relationship between a team’s average draw and take-out success percentages over the games in the dataset, based on the T{1,2}DrawsGamePercent and T{1,2}TOGamePercent columns. Each point represents a national team, and its size reflects the number of games played. The strongest overall performers include Great Britain, Canada, Sweden, Italy, Japan, USA, Norway, Estonia, and Switzerland, all averaging above 75% in both draw and take-out success. These results suggest that consistent shot-making ability in both draws and take-outs strategies is strongly related to team success.

![Refer to caption](2512.16574v2/Manuscript_images/image13.png)

Most top-performing teams exhibit a balanced proficiency in both draws and take-outs, clustering near the top-right quadrant of the plot. However, the majority of teams have a superior performance in draws compared to take-outs. The scoring in curling is on a 0-100 scale (taking only steps of 25) and describes the success of the shot. A draw missed by half a foot may still get a score of 75, but a take-out missed by an inch can cause irreparable damage to an end and get a score of 0. A new scoring system that incorporates the level of difficulty of a shot could help to better evaluate team and player performances.

The game-level dataset also captures nuanced strategic behavior, such as Power Play selection timing and hammer vs. first stone possession. These can be integrated with end-level and shot-level data to model more complex dynamics, such as momentum shifts, comeback likelihoods, or optimal Power Play usage patterns across games.

### IV-D Team-Level Analysis

Since athlete participation can vary from year to year, analyses are conducted primarily at the country level rather than at the individual player or team level, thereby increasing sample sizes and ensuring comparability across tournaments.

To assess team performance, we adopt the efficiency metrics proposed by [Palmer et al. (2019)](#bib.bib11) and adapt them for mixed doubles as follows,

Hammer Efficiency (HE): Proportion of ends with hammer where a team scores 2 or more points.

Force Efficiency (FE): Proportion of ends without hammer where a team holds the opponent to one or zero points. Unlike traditional curling, we include blanked ends in this definition as the change in hammer possession benefits the team without hammer, although these rarely occur in mixed doubles.

Steal Efficiency (SE): Proportion of ends where a team scores at least one point without hammer.

These efficiency metrics are presented in Table [II](#S4.T2 "TABLE II ‣ IV-D Team-Level Analysis ‣ IV Results and Insights from the Mixed Doubles Curling Dataset ‣ Opening the House: Datasets for Mixed Doubles Curling"), both for standard ends and Power Play ends. Notably:

Canada leads in standard Hammer Efficiency (40.73%).

Japan achieves the highest Force Efficiency (40.11%).

Ireland tops Steal Efficiency at 51.28%.

In Power Play situations, Israel dominates Hammer Efficiency, while Austria and France lead in Force and Steal Efficiencies, respectively, although all of these teams have played a relatively small number of games which as indicated in the parentheses in Table [II](#S4.T2 "TABLE II ‣ IV-D Team-Level Analysis ‣ IV Results and Insights from the Mixed Doubles Curling Dataset ‣ Opening the House: Datasets for Mixed Doubles Curling") next to the proportions.

| Country | HE | PP-HE | FE | PP-FE | SE | PP-SE |
| --- | --- | --- | --- | --- | --- | --- |
| CAN-Canada | 0.4073 (275) | 0.4407 (59) | 0.3732 (284) | 0.3647 (85) | 0.4648 (284) | 0.3059 (85) |
| SWE-Sweden | 0.3704 (216) | 0.4561 (57) | 0.3550 (231) | 0.3099 (71) | 0.4372 (231) | 0.3662 (71) |
| SCO-Scotland | 0.3702 (235) | 0.4507 (71) | 0.3577 (246) | 0.3239 (71) | 0.4350 (246) | 0.3380 (71) |
| SUI-Switzerland | 0.3402 (244) | 0.3385 (65) | 0.3252 (246) | 0.2632 (76) | 0.4187 (246) | 0.3421 (76) |
| JPN-Japan | 0.3371 (175) | 0.3750 (56) | 0.4011 (177) | 0.2453 (53) | 0.3503 (177) | 0.3962 (53) |
| LAT-Latvia | 0.3214 (28) | 0.5556 (9) | 0.2188 (32) | 0.2500 (8) | 0.4688 (32) | 0.5000 (8) |
| ITA-Italy | 0.3206 (209) | 0.4200 (50) | 0.2712 (236) | 0.2727 (66) | 0.4703 (236) | 0.3788 (66) |
| RCF-Rcf | 0.3091 (110) | 0.3333 (27) | 0.3017 (116) | 0.4074 (27) | 0.3707 (116) | 0.2222 (27) |
| USA-United States | 0.3077 (234) | 0.3676 (68) | 0.2989 (271) | 0.2840 (81) | 0.4502 (271) | 0.3704 (81) |
| CHN-China | 0.3068 (176) | 0.3774 (53) | 0.3333 (192) | 0.2653 (49) | 0.3750 (192) | 0.4286 (49) |
| NOR-Norway | 0.2915 (247) | 0.4750 (80) | 0.3377 (305) | 0.3182 (88) | 0.4557 (305) | 0.3750 (88) |
| AUS-Australia | 0.2806 (196) | 0.4000 (55) | 0.2878 (205) | 0.3214 (56) | 0.4049 (205) | 0.4107 (56) |
| BLR-Belarus | 0.2800 (25) | 0.2857 (7) | 0.2632 (19) | 0.4000 (5) | 0.3158 (19) | 0.2000 (5) |
| FIN-Finland | 0.2745 (153) | 0.3404 (47) | 0.2614 (153) | 0.2250 (40) | 0.3987 (153) | 0.2250 (40) |
| GER-Germany | 0.2743 (175) | 0.2955 (44) | 0.3046 (151) | 0.4000 (45) | 0.4106 (151) | 0.3333 (45) |
| ENG-England | 0.2712 (118) | 0.3056 (36) | 0.3028 (109) | 0.2308 (26) | 0.2752 (109) | 0.2692 (26) |
| TUR-Türkiye | 0.2703 (148) | 0.2381 (42) | 0.3333 (123) | 0.1795 (39) | 0.3333 (123) | 0.3846 (39) |
| HUN-Hungary | 0.2667 (120) | 0.5000 (40) | 0.2441 (127) | 0.3235 (34) | 0.3543 (127) | 0.2059 (34) |
| KOR-Korea | 0.2621 (206) | 0.3710 (62) | 0.2906 (203) | 0.4407 (59) | 0.3990 (203) | 0.3051 (59) |
| EST-Estonia | 0.2538 (197) | 0.3898 (59) | 0.3048 (187) | 0.2963 (54) | 0.4439 (187) | 0.3704 (54) |
| CZE-Czech Republic | 0.2500 (224) | 0.3051 (59) | 0.3227 (220) | 0.3833 (60) | 0.4182 (220) | 0.2500 (60) |
| IRL-Ireland | 0.2424 (33) | 0.5000 (10) | 0.1795 (39) | 0.1667 (12) | 0.5128 (39) | 0.3333 (12) |
| ISR-Israel | 0.2273 (22) | 0.5714 (7) | 0.2941 (17) | 0.4000 (5) | 0.2353 (17) | 0.0000 (5) |
| DEN-Denmark | 0.2057 (141) | 0.1500 (40) | 0.3333 (126) | 0.2564 (39) | 0.4444 (126) | 0.4103 (39) |
| ESP-Spain | 0.2037 (162) | 0.2917 (48) | 0.3267 (150) | 0.3158 (38) | 0.3267 (150) | 0.3421 (38) |
| AUT-Austria | 0.1852 (54) | 0.4737 (19) | 0.2381 (63) | 0.4667 (15) | 0.3810 (63) | 0.0667 (15) |
| SVK-Slovakia | 0.1818 (22) | 0.4000 (10) | 0.2903 (31) | 0.1429 (7) | 0.3226 (31) | 0.5714 (7) |
| NED-Netherlands | 0.1759 (108) | 0.1333 (30) | 0.3103 (87) | 0.2593 (27) | 0.3333 (87) | 0.3704 (27) |
| FRA-France | 0.1698 (53) | 0.2000 (15) | 0.2083 (48) | 0.2000 (10) | 0.4375 (48) | 0.6000 (10) |
| POL-Poland | 0.1500 (20) | 0.2857 (7) | 0.2941 (17) | 0.1667 (6) | 0.2941 (17) | 0.1667 (6) |
| Weighted Average | 0.2820 (119) | 0.358 (34) | 0.3127 (119) | 0.3034 (34) | 0.4053 (119) | 0.3402 (34) |

Interestingly, few teams maintain above-average performance across all efficiency types, highlighting the complexity of mastering both offensive and defensive play, especially with the added strategic layer introduced by the Power Play. The relatively low sample size per team—at most one offensive and one defensive Power Play opportunity per game—limits opportunities for in-game learning and optimization. Looking closer at the Power Play, teams are expected to have a higher Hammer efficiency with the Power Play than without. For many teams, such as Switzerland, Türkiye, Denmark and the Netherlands, this is not the case. Perhaps these teams prefer to use the Power Play in a defensive manner to limit steals or simply take one point, but typically we expect higher values here. Similarly with the Steal efficiency, we expect a lower SE in the Power Play than otherwise, but for teams like Japan, Latvia, and China, their PP-SE is greater than SE. Perhaps these teams have a defensive edge in the Power Play that other teams are not prepared for.

Compared to traditional curling, the mixed doubles game reveals marked differences. [Palmer et al. (2019)](#bib.bib11) report Force Efficiencies between 45%–65% in traditional curling, whereas the highest in mixed doubles is just 40% even though we expanded the definition to include blanks. This is likely due to the higher frequency of steals in the mixed doubles format. Similarly, Hammer Efficiencies in standard curling range from 30%–50%, while the weighted average in mixed doubles is approximately 28%, indicating a scoring environment that is generally more evenly distributed among competitors.

These insights reinforce the conclusion that mixed doubles curling requires distinct strategic approaches and that modeling efforts must be tailored to this format, rather than relying on frameworks developed for traditional 4-player curling.

## V Summary of Contributions

In this work, we present the most comprehensive and structured dataset to date for mixed doubles curling, a sport that continues to evolve both competitively and analytically. We detail the processes involved in data collection, cleaning, and feature engineering, resulting in a dataset that spans nearly a decade, with over 60,000 shots, 1,100 games, and representation from 53 countries.

Our brief summary analysis highlights the unique dynamics of mixed doubles curling—differentiating it from traditional curling in key areas such as scoring distributions, shot success rates, and team strategies. We explore this through a multi-level analysis:

At the shot level, we discuss shot types and grading results, highlighting the relative success rates of different throws.

At the end level, we analyze scoring patterns and the strategic impact of the Power Play, uncovering how it shifts scoring proportions and changes steal likelihoods across game contexts.

At the game level, we aggregate performance metrics such as draw and take-out success rates to identify traits of top-performing teams.

At the team level, we extend established standard curling metrics (e.g., Hammer, Force, and Steal Efficiencies) to the mixed doubles format and quantify their values in both standard and Power Play ends.

Our findings reveal that mixed doubles curling exhibits distinct structural and strategic differences compared to traditional curling. For example, the higher rate of steals, the near absence of blank ends, and the tactical use of the Power Play create novel decision-making challenges for teams. These elements make the findings from traditional curling analytics inappropriate for mixed doubles, reinforcing the need for tailored analytical tools.

We envision this dataset as a launching point for a wide range of future research. Potential directions include optimal Power Play timing and defense, role-based performance modeling (e.g., stone order assignments), in-game win probability estimation, and broader player/team evaluation frameworks. By making this data available and demonstrating its analytical potential, we aim to support the continued growth of mixed doubles curling through evidence-based strategies and performance insights.

## References

## VI Supplementary Material

### VI-A Text Scraping Corrections

Although most tournaments followed consistent formatting, several exceptions required manual intervention to ensure a complete and standardized dataset. Below we summarize the main categories of corrections applied.

Tournament Metadata

Some title pages were embedded as images and could not be parsed automatically through text scraping; tournament name, location, and dates were entered manually.

Roster, Player and Staff Information

Name formatting: Inconsistent capitalization or abbreviation occasionally disrupted parsing (e.g., McFADZEAN with lowercase “c”).

Non-unique identifiers: Cases where two players shared the same abbreviation (e.g., Maia and Magnus Ramsfjell both listed as RAMSFJELL M) required external verification via video sources.

Abbreviated first names: Some entries (e.g., HAMILTON B for Rebecca “Becca” Hamilton) were harmonized to ensure consistent player tracking across tournaments.

Missing attributes: Handedness varied across years; in such cases, we standardized fields and coded unavailable values as missing.

Game Results Pages

Power Play inconsistencies: In some events (e.g., 2016 WMDCC), Power Plays were not identified or were mis-attributed. These were verified using shot by shot images and hammer possession.

Shot success analysis: Early Results Books (e.g., 2016 WMDCC) lacked rotation-specific breakdowns. These omissions were flagged and coded as missing.

Formatting issues: Long player names were occasionally split across lines, requiring manual reassembly.

Shot by shot Data

Partial availability: In some years (e.g., 2018–2019 WMDCC), shot by shot results were only recorded for playoff rounds.

Ambiguous shooters: Instances of mislabeled or blank shooter fields were corrected manually (e.g., “Power Play” erroneously listed as the shooter, or missing shooter names).

Missing shots: Rare cases of absent shot records (e.g., a missing shot 2 in the 2018 WMDCC, NOR–ITA, End 4 shown in Figure [14](#S6.F14 "Fig. 14 ‣ VI-A Text Scraping Corrections ‣ VI Supplementary Material ‣ Opening the House: Datasets for Mixed Doubles Curling")) were filled with null entries to preserve sequencing.

Rotation and rating formats: Differences in notation (e.g., In/Out vs. Clockwise/Counterclockwise) and rating scales (0–4 vs. 0–100%) were standardized.

![Refer to caption](2512.16574v2/Supplemental_Material_images/image14.png)

### VI-B Image Extraction Corrections

Table [III](#S6.T3 "TABLE III ‣ VI-B Image Extraction Corrections ‣ VI Supplementary Material ‣ Opening the House: Datasets for Mixed Doubles Curling") documents the tournaments, games, ends, and teams where manual corrections to shot by shot images were necessary. The most common issues were:

Missing images – prepositioned stone or regular shot images absent from the Results Booklets.

Duplicated images – the prepositioned stones image duplicated from the first shot image.

Examples of the pages with missing or incorrect shots are show in Figures [14](#S6.F14 "Fig. 14 ‣ VI-A Text Scraping Corrections ‣ VI Supplementary Material ‣ Opening the House: Datasets for Mixed Doubles Curling") and [15](#S6.F15 "Fig. 15 ‣ VI-B Image Extraction Corrections ‣ VI Supplementary Material ‣ Opening the House: Datasets for Mixed Doubles Curling").

| Tournament | Game | End | Team 1 | Team 2 | Description |
| --- | --- | --- | --- | --- | --- |
| WMDCC 2017 | Round Robin Session 4 | 5 | Switzerland | Romania | Prepositioned image duplicate of shot 1 |
| WMDCC 2017 | Round Robin Session 8 | 5 | Türkiye | Czech Republic | Prepositioned image duplicate of shot 1 |
| WMDCC 2017 | Round Robin Session 9 | 8 | Israel | Australia | Prepositioned image duplicate of shot 1 |
| WMDCC 2017 | Round Robin Session 13 | 3 | Brazil | Hungary | Prepositioned image duplicate of shot 1 |
| WMDCC 2017 | Round Robin Session 17 | 5 | Spain | Switzerland | Prepositioned image missing |
| WMDCC 2017 | Round Robin Session 21 | 5 | Finland | Brazil | Prepositioned image duplicate of shot 1 |
| WMDCC 2017 | Round Robin Session 23 | 6 | RCF | New Zealand | Prepositioned image duplicate of shot 1 |
| WMDCC 2017 | Round Robin Session 26 | 3 | Slovenia | Romania | Prepositioned image duplicate of shot 1 |
| WMDCC 2017 | Round Robin Session 26 | 6 | Norway | Ireland | Prepositioned image duplicate of shot 1 |
| WMDCC 2017 | Round Robin Session 27 | 3 | New Zealand | Switzerland | Prepositioned image missing |
| WMDCC 2018 | B-side Rank 11-12 | 4 | Norway | Italy | Shot 2 missing |
| OWG 2018 | Round Robin Session 1 | 5 | United States | OAR | Prepositioned image missing |
| OWG 2018 | Semi-final | 8 | Canada | Norway | Prepositioned image missing |
| WMDCC 2022 | Round Robin Session 13 | 3 | Italy | Switzerland | Prepositioned image missing |
| WMDCC 2022 | Round Robin Session 18 | 2 | Germany | England | Prepositioned image missing |
| WMDCC 2024 | Round Robin Session 14 | 2 | China | Canada | Prepositioned image missing |
| WMDCC 2025 | Round Robin Session 2 | 8 | Australia | Switzerland | Prepositioned image missing |
| WMDCC 2025 | Round Robin Session 3 | 2 | Sweden | Netherlands | Prepositioned image duplicate of shot 1 |

![Refer to caption](2512.16574v2/Supplemental_Material_images/image15.png)

### VI-C Supplementary Material: Column Definitions

The game- and shot-level dataset column descriptions are provided in Tables [VI-D](#S6.SS4 "VI-D Supplementary Material: Scoring Distributions ‣ VI Supplementary Material ‣ Opening the House: Datasets for Mixed Doubles Curling") and [VI-D](#S6.SS4 "VI-D Supplementary Material: Scoring Distributions ‣ VI Supplementary Material ‣ Opening the House: Datasets for Mixed Doubles Curling"). Options within {} are used to identify multiple columns of that type. For example T{1,2} identifies that there is one column called T1 and another called T2 representing the two teams playing in the game.

### VI-D Supplementary Material: Scoring Distributions

In addition to the figures provided in Section [IV-B](#S4.SS2 "IV-B End-Level Analysis ‣ IV Results and Insights from the Mixed Doubles Curling Dataset ‣ Opening the House: Datasets for Mixed Doubles Curling"), we further split the scoring distributions for the hammer team by score differential and end (Figure [16](#S6.F16 "Fig. 16 ‣ VI-D Supplementary Material: Scoring Distributions ‣ VI Supplementary Material ‣ Opening the House: Datasets for Mixed Doubles Curling")) and by score differential and Power Play usage (Figure [17](#S6.F17 "Fig. 17 ‣ VI-D Supplementary Material: Scoring Distributions ‣ VI Supplementary Material ‣ Opening the House: Datasets for Mixed Doubles Curling")). Sample size has an effect on the results, which is visible when separating the data by Power Play usage. For example, only one team has used the Power Play in end 1 and, thus, was the only team to have the advantage unavailable in the second end.

|  |  |
| --- | --- |
| Game by game dataset details |  |
| Column | Description |
| ID | Tournament identifier, a combination of the abbreviation of the tournament and the year. |
| Title | Name of the game, typically round robin or playoff label. |
| Game | Increment number for the game, gold medal game is game 1 and the largest number is first round robin game of the tournament. |
| Sheet | Sheet label (when available). |
| T{1,2} | Team names. |
| LineScoreT{1,2} | End by end breakdown of what the team scored. |
| FinalT{1,2} | Score at the conclusion of the game. |
| LSFE | Indicator for Last Stone First End winner. |
| T{1,2}\_Colour | Stone colour of each team. |
| PP\_E{1,2} | Identifiers for the ends that had a Power Play. |
| Left\_PP\_E{1,2} | Indicator for whether the Power Play was on the left side of the sheet. |
| T{1,2}{F,M}Name | Name of team member by gender. |
| T{1,2}{F,M}{Draws,TO,Total}{Clock,Counter}Num | Number of shots per team member per shot type or total for the tournament thus far separated by stone rotation. |
| T{1,2}{F,M}{Draws,TO,Total}{Clock,Counter}Percent | Outcome percentages of shots per team member per shot type or total for the tournament thus far separated by stone rotation. |
| T{1,2}{F,M}{Draws,TO,Total}GameNum | Number of total shots per team member per shot type or total for the tournament thus far. |
| T{1,2}{F,M}{Draws,TO,Total}GamePercent | Outcome percentages of total shots per team member per shot type or total for the tournament thus far. |
| T{1,2}{Draws,TO,Total}{Clock,Counter}Num | Number of shots per team per shot type or total for the tournament thus far separated by stone rotation. |
| T{1,2}{Draws,TO,Total}{Clock,Counter}Percent | Outcome percentages of shots per team per shot type or total for the tournament thus far separated by stone rotation. |
| T{1,2}{Draws,TO,Total}GameNum | Number of total shots per team per shot type or total for the tournament thus far. |
| T{1,2}{Draws,TO,Total}GamePercent | Outcome percentages of total shots per team per shot type or total for the tournament thus far. |
| T{1,2}{F,M,Total}Game | Number of shots per team member for the game. |
| T{1,2}{F,M,Total}All | Outcome percentages of shots per team member for the tournament thus far. |
| T{1,2}Mins | Minutes remaining on the shot clock at the end of the game by team. |
| T{1,2}Secs | Seconds remaining on the shot clock at the end of the game by team. |
| EE-T{1,2}Mins | Extra ends minutes remaining on the shot clock at the end of the game by team. |
| EE-T{1,2}Secs | Extra ends seconds remaining on the shot clock at the end of the game by team. |
| T{1,2}Time-out{1,2}\_End | Time-out end that the team called each of their two time-outs. |
| T{1,2}Time-out{1,2}\_Shot | Time-out shot number that the team called each of their two time-outs. |
| T{1,2}\_{F,M}\_LSFE\_Turn | Last stone draw rotation per team member. |
| T{1,2}\_{F,M}\_LSFE\_Distance | Last stone draw distance to the pin per team member. |
| T{1,2}\_LSFE\_TotalDistance | Team’s cumulative last stone draw distance to the pin. |

|  |  |
| --- | --- |
| Shot by Shot dataset details |  |
| Column | Description |
| ID | Tournament identifier, a combination of the abbreviation of the tournament and the year. |
| Title | Name of the game, typically round robin or playoff game. |
| Game | Increment number for the game, gold medal game is game 1 and the largest number is first round robin game of the tournament. |
| Sheet | Sheet label (when available). |
| T{1,2} | Team names. |
| T{1,2}\_Colour | Stone colour of each team. |
| T{1,2}{F,M}Name | Names of the female and male members of each team. |
| LSFE | Indicator for last stone first end winner. |
| End | Number of the end. |
| Hammer\_End | Name of the team with hammer possession in the end. |
| Shot | Number of the shot, 0 indicates prepositioned stones. |
| Rock\_Country | Name of the team throwing the stone. |
| Rank | Final standing ranking, 1 indicates the tournament winner, -1 indicates the team was disqualified. |
| Gender | Gender of the player throwing the shot. |
| Thrower | Name of the player throwing the shot. |
| Handedness | Handedness of the thrower. |
| Throw | Type of throw (e.g. Draw, Take-out, etc.). |
| Turn | Rotation of the throw. |
| Percent | Score of the shot (0%, 25%, 50%, 75%, or 100%). |
| {R,Y}{1,2,3,4,5,6}{X,Y} | Shot identifier, combination of the rocks colour, number and Y or X coordinate. The number is not necessarily the order it was shot but rather the order in which the algorithm identified it. |
| ShooterCol | Colour of the shooter stone. The shooter is identified by a bold black outline or a black dot in its center. |
| Shooter{X,Y} | Coordinates of the shooter stone. |
| {Left,Right}\_PP | Indicator for whether the Power Play has on the right or left side of the sheet. |
| PowerPlay | Indicator for if the end is a Power Play. |
| PP\_Team | Identifier for the team that called the Power Play and hence had prepositioned stone placement selection in that end. |
| T{1,2}\_has\_PP\_available | Indicator for whether or not the team has a Power Play available during that end. The indicator is 1 during the Power Play end and also even when the team doesn’t have the hammer and are unable to use it in the given end. |
| T{1,2}Before | The score for the team prior to the end. |
| T{1,2}During | The amount of points the team scored as a result of the end. X if the game was conceded during the end. |
| T{1,2}After | T{1,2}Before + T{1,2}During. X if the game was conceded during the end. |
| FinalT{1,2} | Score at the conclusion of the game. |
| {Red,Yellow}\_Score | Number of each colours stones in the house and closer to the pin than the opposite colour, thus the score at the conclusion of the shot. |
| {Red,Yellow}\_House | Number of each colours stones in the house. |
| {Red,Yellow}\_Button | Number of each colours stones on the button. |
| {Red,Yellow}\_{4,8,12}FT | Number of each colours stones in the ring of that size. |
| {Red,Yellow}\_W{1,…,10} | Number of each colours stones in the playing zone split by weight class, see Figure [6](#S3.F6 "Fig. 6 ‣ III-D Post-Processing ‣ III Data collection ‣ Opening the House: Datasets for Mixed Doubles Curling"). |
| {Red,Yellow}\_G{L,C,R} | Number of each colours stones in the playing zone split by guard side, see Figure [6](#S3.F6 "Fig. 6 ‣ III-D Post-Processing ‣ III Data collection ‣ Opening the House: Datasets for Mixed Doubles Curling"). |

![Refer to caption](2512.16574v2/Supplemental_Material_images/image16.png)
![Refer to caption](2512.16574v2/Supplemental_Material_images/image17.png)
![[LOGO]](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAsAAAAOCAYAAAD5YeaVAAAAAXNSR0IArs4c6QAAAAZiS0dEAP8A/wD/oL2nkwAAAAlwSFlzAAALEwAACxMBAJqcGAAAAAd0SU1FB9wKExQZLWTEaOUAAAAddEVYdENvbW1lbnQAQ3JlYXRlZCB3aXRoIFRoZSBHSU1Q72QlbgAAAdpJREFUKM9tkL+L2nAARz9fPZNCKFapUn8kyI0e4iRHSR1Kb8ng0lJw6FYHFwv2LwhOpcWxTjeUunYqOmqd6hEoRDhtDWdA8ApRYsSUCDHNt5ul13vz4w0vWCgUnnEc975arX6ORqN3VqtVZbfbTQC4uEHANM3jSqXymFI6yWazP2KxWAXAL9zCUa1Wy2tXVxheKA9YNoR8Pt+aTqe4FVVVvz05O6MBhqUIBGk8Hn8HAOVy+T+XLJfLS4ZhTiRJgqIoVBRFIoric47jPnmeB1mW/9rr9ZpSSn3Lsmir1fJZlqWlUonKsvwWwD8ymc/nXwVBeLjf7xEKhdBut9Hr9WgmkyGEkJwsy5eHG5vN5g0AKIoCAEgkEkin0wQAfN9/cXPdheu6P33fBwB4ngcAcByHJpPJl+fn54mD3Gg0NrquXxeLRQAAwzAYj8cwTZPwPH9/sVg8PXweDAauqqr2cDjEer1GJBLBZDJBs9mE4zjwfZ85lAGg2+06hmGgXq+j3+/DsixYlgVN03a9Xu8jgCNCyIegIAgx13Vfd7vdu+FweG8YRkjXdWy329+dTgeSJD3ieZ7RNO0VAXAPwDEAO5VKndi2fWrb9jWl9Esul6PZbDY9Go1OZ7PZ9z/lyuD3OozU2wAAAABJRU5ErkJggg==)

## Instructions for reporting errors

We are continuing to improve HTML versions of papers, and your feedback helps enhance accessibility and mobile
support. To report errors in the HTML that will help us improve conversion and rendering, choose any of the
methods listed below:

**Tip:** You can select the relevant text first, to include it in your report.

Our team has already identified [the following issues](https://github.com/arXiv/html_feedback/issues). We appreciate your time reviewing and reporting rendering errors we
may not have found yet. Your efforts will help us improve the HTML versions for all readers, because disability
should not be a barrier to accessing research. Thank you for your continued support in championing open access for
all.

Have a free development cycle? Help support accessibility at arXiv! Our collaborators at LaTeXML maintain a [list of packages that need conversion](https://github.com/brucemiller/LaTeXML/wiki/Porting-LaTeX-packages-for-LaTeXML), and welcome [developer contributions](https://github.com/brucemiller/LaTeXML/issues).

![Simons Foundation](/static/base/1.0.1/images/funders/simons-foundation.png)
![Simons Foundation International](/static/base/1.0.1/images/funders/simons-foundation-international.png)
![Schmidt Sciences](/static/base/1.0.1/images/funders/schmidt-sciences.png)